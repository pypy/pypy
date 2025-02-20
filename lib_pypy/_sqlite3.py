#-*- coding: utf-8 -*-
# pysqlite2/dbapi.py: pysqlite DB-API module
#
# Copyright (C) 2007-2008 Gerhard Häring <gh@ghaering.de>
#
# This file is part of pysqlite.
#
# This software is provided 'as-is', without any express or implied
# warranty.  In no event will the authors be held liable for any damages
# arising from the use of this software.
#
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely, subject to the following restrictions:
#
# 1. The origin of this software must not be misrepresented; you must not
#    claim that you wrote the original software. If you use this software
#    in a product, an acknowledgment in the product documentation would be
#    appreciated but is not required.
# 2. Altered source versions must be plainly marked as such, and must not be
#    misrepresented as being the original software.
# 3. This notice may not be removed or altered from any source distribution.
#
# Note: This software has been modified for use in PyPy.

import datetime
import os
import string
import struct
import sys
import threading
import traceback
import types
import weakref
import operator
from collections import OrderedDict
from functools import wraps

try:
    from __pypy__ import newlist_hint, add_memory_pressure
except ImportError:
    assert '__pypy__' not in sys.builtin_module_names
    newlist_hint = lambda sizehint: []
    add_memory_pressure = lambda size: None

if sys.version_info[0] >= 3:
    StandardError = Exception
    cmp = lambda x, y: (x > y) - (x < y)
    long = int
    xrange = range
    basestring = unicode = str
    buffer = memoryview
    _BLOB_TYPE = bytes
else:
    _BLOB_TYPE = buffer

from _sqlite3_cffi import ffi as _ffi, lib as _lib

_UNSUPPORTED_TYPE = object()

exported_sqlite_symbols = [
    'SQLITE_ABORT',
    'SQLITE_ABORT_ROLLBACK',
    'SQLITE_ALTER_TABLE',
    'SQLITE_ANALYZE',
    'SQLITE_ATTACH',
    'SQLITE_AUTH',
    'SQLITE_AUTH_USER',
    'SQLITE_BUSY',
    'SQLITE_BUSY_RECOVERY',
    'SQLITE_BUSY_SNAPSHOT',
    'SQLITE_BUSY_TIMEOUT',
    'SQLITE_CANTOPEN',
    'SQLITE_CANTOPEN_CONVPATH',
    'SQLITE_CANTOPEN_DIRTYWAL',
    'SQLITE_CANTOPEN_FULLPATH',
    'SQLITE_CANTOPEN_ISDIR',
    'SQLITE_CANTOPEN_NOTEMPDIR',
    'SQLITE_CANTOPEN_SYMLINK',
    'SQLITE_CONSTRAINT',
    'SQLITE_CONSTRAINT_CHECK',
    'SQLITE_CONSTRAINT_COMMITHOOK',
    'SQLITE_CONSTRAINT_FOREIGNKEY',
    'SQLITE_CONSTRAINT_FUNCTION',
    'SQLITE_CONSTRAINT_NOTNULL',
    'SQLITE_CONSTRAINT_PINNED',
    'SQLITE_CONSTRAINT_PRIMARYKEY',
    'SQLITE_CONSTRAINT_ROWID',
    'SQLITE_CONSTRAINT_TRIGGER',
    'SQLITE_CONSTRAINT_UNIQUE',
    'SQLITE_CONSTRAINT_VTAB',
    'SQLITE_CORRUPT',
    'SQLITE_CORRUPT_INDEX',
    'SQLITE_CORRUPT_SEQUENCE',
    'SQLITE_CORRUPT_VTAB',
    'SQLITE_CREATE_INDEX',
    'SQLITE_CREATE_TABLE',
    'SQLITE_CREATE_TEMP_INDEX',
    'SQLITE_CREATE_TEMP_TABLE',
    'SQLITE_CREATE_TEMP_TRIGGER',
    'SQLITE_CREATE_TEMP_VIEW',
    'SQLITE_CREATE_TRIGGER',
    'SQLITE_CREATE_VIEW',
    'SQLITE_CREATE_VTABLE',
    'SQLITE_DELETE',
    'SQLITE_DENY',
    'SQLITE_DETACH',
    'SQLITE_DONE',
    'SQLITE_DROP_INDEX',
    'SQLITE_DROP_TABLE',
    'SQLITE_DROP_TEMP_INDEX',
    'SQLITE_DROP_TEMP_TABLE',
    'SQLITE_DROP_TEMP_TRIGGER',
    'SQLITE_DROP_TEMP_VIEW',
    'SQLITE_DROP_TRIGGER',
    'SQLITE_DROP_VIEW',
    'SQLITE_DROP_VTABLE',
    'SQLITE_EMPTY',
    'SQLITE_ERROR',
    'SQLITE_ERROR_MISSING_COLLSEQ',
    'SQLITE_ERROR_RETRY',
    'SQLITE_ERROR_SNAPSHOT',
    'SQLITE_FORMAT',
    'SQLITE_FULL',
    'SQLITE_FUNCTION',
    'SQLITE_IGNORE',
    'SQLITE_INSERT',
    'SQLITE_INTERNAL',
    'SQLITE_INTERRUPT',
    'SQLITE_IOERR',
    'SQLITE_IOERR_ACCESS',
    'SQLITE_IOERR_AUTH',
    'SQLITE_IOERR_BEGIN_ATOMIC',
    'SQLITE_IOERR_BLOCKED',
    'SQLITE_IOERR_CHECKRESERVEDLOCK',
    'SQLITE_IOERR_CLOSE',
    'SQLITE_IOERR_COMMIT_ATOMIC',
    'SQLITE_IOERR_CONVPATH',
    'SQLITE_IOERR_CORRUPTFS',
    'SQLITE_IOERR_DATA',
    'SQLITE_IOERR_DELETE',
    'SQLITE_IOERR_DELETE_NOENT',
    'SQLITE_IOERR_DIR_CLOSE',
    'SQLITE_IOERR_DIR_FSYNC',
    'SQLITE_IOERR_FSTAT',
    'SQLITE_IOERR_FSYNC',
    'SQLITE_IOERR_GETTEMPPATH',
    'SQLITE_IOERR_LOCK',
    'SQLITE_IOERR_MMAP',
    'SQLITE_IOERR_NOMEM',
    'SQLITE_IOERR_RDLOCK',
    'SQLITE_IOERR_READ',
    'SQLITE_IOERR_ROLLBACK_ATOMIC',
    'SQLITE_IOERR_SEEK',
    'SQLITE_IOERR_SHMLOCK',
    'SQLITE_IOERR_SHMMAP',
    'SQLITE_IOERR_SHMOPEN',
    'SQLITE_IOERR_SHMSIZE',
    'SQLITE_IOERR_SHORT_READ',
    'SQLITE_IOERR_TRUNCATE',
    'SQLITE_IOERR_UNLOCK',
    'SQLITE_IOERR_VNODE',
    'SQLITE_IOERR_WRITE',
    'SQLITE_LIMIT_ATTACHED',
    'SQLITE_LIMIT_COLUMN',
    'SQLITE_LIMIT_COMPOUND_SELECT',
    'SQLITE_LIMIT_EXPR_DEPTH',
    'SQLITE_LIMIT_FUNCTION_ARG',
    'SQLITE_LIMIT_LENGTH',
    'SQLITE_LIMIT_LIKE_PATTERN_LENGTH',
    'SQLITE_LIMIT_SQL_LENGTH',
    'SQLITE_LIMIT_TRIGGER_DEPTH',
    'SQLITE_LIMIT_VARIABLE_NUMBER',
    'SQLITE_LIMIT_VDBE_OP',
    'SQLITE_LIMIT_WORKER_THREADS',
    'SQLITE_LOCKED',
    'SQLITE_LOCKED_SHAREDCACHE',
    'SQLITE_LOCKED_VTAB',
    'SQLITE_MISMATCH',
    'SQLITE_MISUSE',
    'SQLITE_NOLFS',
    'SQLITE_NOMEM',
    'SQLITE_NOTADB',
    'SQLITE_NOTFOUND',
    'SQLITE_NOTICE',
    'SQLITE_NOTICE_RECOVER_ROLLBACK',
    'SQLITE_NOTICE_RECOVER_WAL',
    'SQLITE_OK',
    'SQLITE_OK_LOAD_PERMANENTLY',
    'SQLITE_OK_SYMLINK',
    'SQLITE_PERM',
    'SQLITE_PRAGMA',
    'SQLITE_PROTOCOL',
    'SQLITE_RANGE',
    'SQLITE_READ',
    'SQLITE_READONLY',
    'SQLITE_READONLY_CANTINIT',
    'SQLITE_READONLY_CANTLOCK',
    'SQLITE_READONLY_DBMOVED',
    'SQLITE_READONLY_DIRECTORY',
    'SQLITE_READONLY_RECOVERY',
    'SQLITE_READONLY_ROLLBACK',
    'SQLITE_RECURSIVE',
    'SQLITE_REINDEX',
    'SQLITE_ROW',
    'SQLITE_SAVEPOINT',
    'SQLITE_SCHEMA',
    'SQLITE_SELECT',
    'SQLITE_TOOBIG',
    'SQLITE_TRANSACTION',
    'SQLITE_UPDATE',
    'SQLITE_WARNING',
    'SQLITE_WARNING_AUTOINDEX',
]


for symbol in exported_sqlite_symbols:
    if hasattr(_lib, symbol): # some only exist on newer sqlite3 versions
        globals()[symbol] = getattr(_lib, symbol)

_SQLITE_TRANSIENT = _lib.SQLITE_TRANSIENT

# error codes

_error_names = {
    globals()[name] : name for name in [
        "SQLITE_ABORT",
        "SQLITE_AUTH",
        "SQLITE_BUSY",
        "SQLITE_CANTOPEN",
        "SQLITE_CONSTRAINT",
        "SQLITE_CONSTRAINT_CHECK",
        "SQLITE_CONSTRAINT_COMMITHOOK",
        "SQLITE_CONSTRAINT_FOREIGNKEY",
        "SQLITE_CONSTRAINT_FUNCTION",
        "SQLITE_CONSTRAINT_NOTNULL",
        "SQLITE_CONSTRAINT_PINNED",
        "SQLITE_CONSTRAINT_PRIMARYKEY",
        "SQLITE_CONSTRAINT_ROWID",
        "SQLITE_CONSTRAINT_TRIGGER",
        "SQLITE_CONSTRAINT_UNIQUE",
        "SQLITE_CONSTRAINT_VTAB",
        "SQLITE_CORRUPT",
        "SQLITE_DONE",
        "SQLITE_EMPTY",
        "SQLITE_ERROR",
        "SQLITE_FORMAT",
        "SQLITE_FULL",
        "SQLITE_INTERNAL",
        "SQLITE_INTERRUPT",
        "SQLITE_IOERR",
        "SQLITE_LOCKED",
        "SQLITE_MISMATCH",
        "SQLITE_MISUSE",
        "SQLITE_NOLFS",
        "SQLITE_NOMEM",
        "SQLITE_NOTADB",
        "SQLITE_NOTFOUND",
        "SQLITE_OK",
        "SQLITE_PERM",
        "SQLITE_PROTOCOL",
        "SQLITE_READONLY",
        "SQLITE_ROW",
        "SQLITE_SCHEMA",
        "SQLITE_TOOBIG",
        "SQLITE_NOTICE",
        "SQLITE_WARNING",
    ]
}

# pysqlite version information
version = "2.6.0"

# pysqlite constants
PARSE_COLNAMES = 1
PARSE_DECLTYPES = 2

# SQLite version information
sqlite_version = str(_ffi.string(_lib.sqlite3_libversion()).decode('ascii'))
_sqlite_version_triple = tuple(int(x) for x in sqlite_version.split('.'))

# flag that signals if base types need adaption
BASE_TYPE_ADAPTED = False

# set of base types that are supported by SQLite3
BASE_TYPES = {bytearray, bytes, float, int, str, NoneType}

class Error(StandardError):
    pass


class Warning(StandardError):
    pass


class InterfaceError(Error):
    pass


class DatabaseError(Error):
    pass


class InternalError(DatabaseError):
    pass


class OperationalError(DatabaseError):
    pass


class ProgrammingError(DatabaseError):
    pass


class IntegrityError(DatabaseError):
    pass


class DataError(DatabaseError):
    pass


class NotSupportedError(DatabaseError):
    pass


def connect(database, timeout=5.0, detect_types=0, isolation_level="",
                 check_same_thread=True, factory=None, cached_statements=100,
                 uri=0):
    factory = Connection if not factory else factory
    # an sqlite3 db seems to be around 100 KiB at least (doesn't matter if
    # backed by :memory: or a file)
    res = factory(database=database, timeout=timeout,
                  detect_types=detect_types, isolation_level=isolation_level,
                  check_same_thread=check_same_thread, factory=factory,
                  cached_statements=cached_statements, uri=uri)
    add_memory_pressure(100 * 1024)
    return res


def _unicode_text_factory(x):
    return unicode(x, 'utf-8')


class _StatementCache(object):
    def __init__(self, connection, maxcount):
        self.connection = connection
        self.maxcount = maxcount
        self.cache = OrderedDict()

    def get(self, sql):
        stat = self.cache.get(sql, None)
        not_there = stat is None
        if not_there or stat._in_use_token:
            stat = object.__new__(Statement)
            stat.__init__(self.connection, sql)
            self.cache[sql] = stat
            if not_there and len(self.cache) > self.maxcount:
                self.cache.popitem(0)
        return stat

BEGIN_STATMENTS = (
    "BEGIN ",
    "BEGIN DEFERRED",
    "BEGIN IMMEDIATE",
    "BEGIN EXCLUSIVE",
)

class Connection(object):
    __initialized = False
    _db = None

    def __init__(self, database, timeout=5.0, detect_types=0, isolation_level="",
                 check_same_thread=True, factory=None, cached_statements=100, uri=0):
        sys.audit("sqlite3.connect", database)
        self.__initialized = False
        db_star = _ffi.new('sqlite3 **')

        database = os.fsencode(database)
        if _lib.SQLITE_OPEN_URI != 0:
            if uri and _lib.SQLITE_OPEN_URI == 0:
                raise NotSupportedError("URIs not supported")
            flags = _lib.SQLITE_OPEN_READWRITE | _lib.SQLITE_OPEN_CREATE
            if uri:
                flags |= _lib.SQLITE_OPEN_URI
            rc = _lib.sqlite3_open_v2(database, db_star, flags, _ffi.NULL)
            if rc != _lib.SQLITE_OK:
                raise self.__exc(OperationalError, "unable to open database file", rc)
        else:
            rc = _lib.sqlite3_open(database, db_star)
            if rc != _lib.SQLITE_OK:
                raise self.__exc(OperationalError, "unable to open database file", rc)
        self.__initialized = True
        self._db = db_star[0]
        if timeout is not None:
            timeout = int(timeout * 1000)  # pysqlite2 uses timeout in seconds
            _lib.sqlite3_busy_timeout(self._db, timeout)

        self.row_factory = None
        self.text_factory = _unicode_text_factory

        self._detect_types = detect_types
        self.isolation_level = isolation_level

        self.__cursors = []
        self.__cursors_counter = 0
        self.__statements = []
        self.__statements_counter = 0
        self.__rawstatements = set()
        self._statement_cache = _StatementCache(self, cached_statements)
        self.__statements_already_committed = []

        self.__blobs = []

        self.__func_cache = {}
        self.__aggregates = {}
        self.__aggregate_instances = {}
        self.__collations = {}
        if check_same_thread:
            self.__thread_ident = threading.get_ident()
        if not check_same_thread and _lib.sqlite3_libversion_number() < 3003001:
            raise NotSupportedError("shared connections not available")

        self.__windows = {}
        self.__window_instances = {}

        self.Error = Error
        self.Warning = Warning
        self.InterfaceError = InterfaceError
        self.DatabaseError = DatabaseError
        self.InternalError = InternalError
        self.OperationalError = OperationalError
        self.ProgrammingError = ProgrammingError
        self.IntegrityError = IntegrityError
        self.DataError = DataError
        self.NotSupportedError = NotSupportedError
        sys.audit("sqlite3.connect/handle", self)

    def __del__(self):
        if self._db:
            _lib.sqlite3_close(self._db)

    def close(self):
        if not self.__initialized:
            raise ProgrammingError("Base Connection.__init__ not called.")
        self._check_thread()

        self.__do_all_statements(Statement._finalize, True)

        # close all blobs
        for blobref in self.__blobs:
            blob = blobref()
            if blob is None:
                continue
            blob.close()
        self.__blobs.clear()

        # depending on when this close() is called, the statements' weakrefs
        # may be already dead, even though Statement.__del__() was not called
        # yet.  In this case, self.__rawstatements is not empty.
        if self.__rawstatements is not None:
            for stmt in list(self.__rawstatements):
                self._finalize_raw_statement(stmt)
            self.__rawstatements = None

        if self._db:
            ret = _lib.sqlite3_close(self._db)
            if ret != _lib.SQLITE_OK:
                raise self._get_exception(ret)
            self._db = None

    def _check_closed(self):
        if not self.__initialized:
            raise ProgrammingError("Base Connection.__init__ not called.")
        if not self._db:
            raise ProgrammingError("Cannot operate on a closed database.")

    def _check_closed_wrap(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            self._check_closed()
            return func(self, *args, **kwargs)
        return wrapper

    def _check_thread(self):
        try:
            if self.__thread_ident == threading.get_ident():
                return
        except AttributeError:
            pass
        else:
            raise ProgrammingError(
                "SQLite objects created in a thread can only be used in that "
                "same thread. The object was created in thread id %d and this "
                "is thread id %d" % (self.__thread_ident, threading.get_ident()))

    def _check_thread_wrap(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            self._check_thread()
            return func(self, *args, **kwargs)
        return wrapper

    def _check_closed_and_thread_wrap(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            self._check_thread()
            self._check_closed()
            return func(self, *args, **kwargs)
        return wrapper

    def _get_exception(self, error_code=None):
        if error_code is None:
            error_code = _lib.sqlite3_errcode(self._db)
        error_message = _ffi.string(_lib.sqlite3_errmsg(self._db)).decode('utf-8')

        if error_code == _lib.SQLITE_OK:
            raise ValueError("error signalled but got SQLITE_OK")
        elif error_code in (_lib.SQLITE_INTERNAL, _lib.SQLITE_NOTFOUND):
            exc = InternalError
        elif error_code == _lib.SQLITE_NOMEM:
            exc = MemoryError
        elif error_code in (
                _lib.SQLITE_ERROR, _lib.SQLITE_PERM, _lib.SQLITE_ABORT,
                _lib.SQLITE_BUSY, _lib.SQLITE_LOCKED, _lib.SQLITE_READONLY,
                _lib.SQLITE_INTERRUPT, _lib.SQLITE_IOERR, _lib.SQLITE_FULL,
                _lib.SQLITE_CANTOPEN, _lib.SQLITE_PROTOCOL, _lib.SQLITE_EMPTY,
                _lib.SQLITE_SCHEMA):
            exc = OperationalError
        elif error_code == _lib.SQLITE_CORRUPT:
            exc = DatabaseError
        elif error_code == _lib.SQLITE_TOOBIG:
            exc = DataError
        elif error_code in (_lib.SQLITE_CONSTRAINT, _lib.SQLITE_MISMATCH):
            exc = IntegrityError
        elif error_code == _lib.SQLITE_MISUSE:
            exc = ProgrammingError
        else:
            exc = DatabaseError
        error_code = _lib.sqlite3_extended_errcode(self._db)
        return self.__exc(exc, error_message, error_code)

    def __exc(self, cls, error_message, error_code):
        exc = cls(error_message)
        exc.error_code = error_code
        exc.sqlite_errorcode = error_code
        if error_code in _error_names:
            exc.sqlite_errorname = _error_names[error_code]
        return exc

    def _remember_cursor(self, cursor):
        self.__cursors.append(weakref.ref(cursor))
        self.__cursors_counter += 1
        if self.__cursors_counter < 200:
            return
        self.__cursors_counter = 0
        self.__cursors = [r for r in self.__cursors if r() is not None]

    def _remember_statement(self, statement):
        self.__rawstatements.add(statement._statement)
        self.__statements.append(weakref.ref(statement))
        self.__statements_counter += 1
        if self.__statements_counter < 200:
            return
        self.__statements_counter = 0
        self.__statements = [r for r in self.__statements if r() is not None]

    def _finalize_raw_statement(self, _statement):
        if self.__rawstatements is not None:
            try:
                self.__rawstatements.remove(_statement)
            except KeyError:
                return    # rare case: already finalized, see issue #2097
            _lib.sqlite3_finalize(_statement)

    def __do_all_statements(self, action, reset_cursors):
        for weakref in self.__statements:
            statement = weakref()
            if statement is not None:
                action(statement)

        if reset_cursors:
            for weakref in self.__cursors:
                cursor = weakref()
                if cursor is not None:
                    cursor._reset = True

    def _reset_already_committed_statements(self):
        lst = self.__statements_already_committed
        self.__statements_already_committed = []
        for weakref in lst:
            statement = weakref()
            if statement is not None:
                statement._force_reset()

    @_check_thread_wrap
    @_check_closed_wrap
    def __call__(self, sql):
        return self._statement_cache.get(sql)

    def _default_cursor_factory(self):
        return Cursor(self)

    def cursor(self, factory=_default_cursor_factory):
        self._check_thread()
        self._check_closed()
        cur = factory(self)
        if not issubclass(type(cur), Cursor):
            raise TypeError("factory must return a cursor, not %s"
                            % (type(cur).__name__,))
        if self.row_factory is not None:
            cur.row_factory = self.row_factory
        return cur

    def execute(self, *args):
        cur = self.cursor()
        return cur.execute(*args)

    def executemany(self, *args):
        cur = self.cursor()
        return cur.executemany(*args)

    def executescript(self, *args):
        cur = self.cursor()
        return cur.executescript(*args)

    def iterdump(self):
        from sqlite3.dump import _iterdump
        self._check_closed()
        return _iterdump(self)

    def _begin(self):
        statement_star = _ffi.new('sqlite3_stmt **')
        ret = _lib.sqlite3_prepare_v2(self._db, self._begin_statement, -1,
                                      statement_star, _ffi.NULL)
        try:
            if ret != _lib.SQLITE_OK:
                raise self._get_exception(ret)
            ret = _lib.sqlite3_step(statement_star[0])
            if ret != _lib.SQLITE_DONE:
                raise self._get_exception(ret)
        finally:
            _lib.sqlite3_finalize(statement_star[0])

    def commit(self):
        self._check_thread()
        self._check_closed()
        if not self.in_transaction:
            return

        # PyPy fix for non-refcounting semantics: since 2.7.13 (and in
        # <= 2.6.x), the statements are not automatically reset upon
        # commit.  However, if this is followed by some specific SQL
        # operations like "drop table", these open statements come in
        # the way and cause the "drop table" to fail.  On CPython the
        # problem is much less important because typically all the old
        # statements are freed already by reference counting.  So here,
        # we copy all the still-alive statements to another list which
        # is usually ignored, except if we get SQLITE_LOCKED
        # afterwards---at which point we reset all statements in this
        # list.
        self.__statements_already_committed = self.__statements[:]

        statement_star = _ffi.new('sqlite3_stmt **')
        ret = _lib.sqlite3_prepare_v2(self._db, b"COMMIT", -1,
                                      statement_star, _ffi.NULL)
        try:
            if ret != _lib.SQLITE_OK:
                raise self._get_exception(ret)
            ret = _lib.sqlite3_step(statement_star[0])
            if ret != _lib.SQLITE_DONE:
                raise self._get_exception(ret)
        finally:
            _lib.sqlite3_finalize(statement_star[0])

    def rollback(self):
        self._check_thread()
        self._check_closed()
        if not self.in_transaction:
            return

        statement_star = _ffi.new('sqlite3_stmt **')
        ret = _lib.sqlite3_prepare_v2(self._db, b"ROLLBACK", -1,
                                      statement_star, _ffi.NULL)
        try:
            if ret != _lib.SQLITE_OK:
                raise self._get_exception(ret)
            ret = _lib.sqlite3_step(statement_star[0])
            if ret != _lib.SQLITE_DONE:
                raise self._get_exception(ret)
        finally:
            _lib.sqlite3_finalize(statement_star[0])

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if exc_type is None and exc_value is None and exc_tb is None:
            self.commit()
        else:
            self.rollback()

    @_check_thread_wrap
    @_check_closed_wrap
    def create_function(self, name, nargs, func, *, deterministic=False):
        try:
            closure = self.__func_cache[func]
        except KeyError:
            @_ffi.callback("void(sqlite3_context*, int, sqlite3_value**)")
            def closure(context, nargs, c_params):
                _function_callback(func, context, nargs, c_params)
            self.__func_cache[func] = closure

        if isinstance(name, unicode):
            name = name.encode('utf-8')
        flags = _lib.SQLITE_UTF8
        if deterministic:
            if not hasattr(_lib, 'SQLITE_DETERMINISTIC'):
                raise NotSupportedError(
                        "deterministic=True requires building _sqlite3 with "
                        "SQLite 3.8.3 or higher")

            if _lib.sqlite3_libversion_number() < 3008003:
                raise NotSupportedError(
                        "deterministic=True requires SQLite 3.8.3 or higher")
            flags |= _lib.SQLITE_DETERMINISTIC
        ret = _lib.sqlite3_create_function(self._db, name, nargs,
                                           flags, _ffi.NULL,
                                           closure, _ffi.NULL, _ffi.NULL)
        if ret != _lib.SQLITE_OK:
            raise self.OperationalError("Error creating function")

    @_check_thread_wrap
    @_check_closed_wrap
    def create_aggregate(self, name, num_args, cls):
        try:
            step_callback, final_callback = self.__aggregates[cls]
        except KeyError:
            step_callback = self.__make_step_callback(cls)
            final_callback = self.__make_final_callback(cls)
            self.__aggregates[cls] = (step_callback, final_callback)

        if isinstance(name, unicode):
            name = name.encode('utf-8')
        ret = _lib.sqlite3_create_function(self._db, name, num_args,
                                           _lib.SQLITE_UTF8, _ffi.NULL,
                                           _ffi.NULL,
                                           step_callback,
                                           final_callback)
        if ret != _lib.SQLITE_OK:
            raise self._get_exception(ret)

    def __make_step_callback(self, cls):
        @_ffi.callback("void(sqlite3_context*, int, sqlite3_value**)")
        def step_callback(context, argc, c_params):
            res = _lib.sqlite3_aggregate_context(context,
                                                 _ffi.sizeof("size_t"))
            aggregate_ptr = _ffi.cast("size_t[1]", res)

            if not aggregate_ptr[0]:
                try:
                    aggregate = cls()
                except Exception as e:
                    msg = (b"user-defined aggregate's '__init__' "
                           b"method raised error")
                    set_sqlite_error(context, msg, e, unraisable_obj=cls)
                    return
                aggregate_id = id(aggregate)
                self.__aggregate_instances[aggregate_id] = aggregate
                aggregate_ptr[0] = aggregate_id
            else:
                aggregate = self.__aggregate_instances[aggregate_ptr[0]]

            try:
                meth = aggregate.step
            except AttributeError as e:
                msg = (b"user-defined aggregate's 'step' "
                       b"method not defined")
                set_sqlite_error(context, msg, e, unraisable_obj=cls)
            else:
                params = _convert_params(context, argc, c_params)
                try:
                    meth(*params)
                except Exception as e:
                    msg = (b"user-defined aggregate's 'step' "
                           b"method raised error")
                    set_sqlite_error(context, msg, e, unraisable_obj=cls)
        return step_callback

    def __make_final_callback(self, cls):
        @_ffi.callback("void(sqlite3_context*)")
        def final_callback(context):
            res = _lib.sqlite3_aggregate_context(context,
                                                 _ffi.sizeof("size_t"))
            aggregate_ptr = _ffi.cast("size_t[1]", res)

            if aggregate_ptr[0]:
                aggregate = self.__aggregate_instances[aggregate_ptr[0]]
                try:
                    try:
                        meth = aggregate.finalize
                    except AttributeError as e:
                        msg = (b"user-defined aggregate's 'finalize' "
                               b"method not defined")
                        set_sqlite_error(context, msg, e, unraisable_obj=cls)
                    else:
                        try:
                            val = meth()
                        except Exception as e:
                            msg = (b"user-defined aggregate's 'finalize' "
                                   b"method raised error")
                            set_sqlite_error(context, msg, e, unraisable_obj=cls)
                        else:
                            _convert_result(context, val)
                finally:
                    del self.__aggregate_instances[aggregate_ptr[0]]
        return final_callback

    @_check_thread_wrap
    @_check_closed_wrap
    def create_collation(self, name, callback):
        if not isinstance(name, str):
            raise TypeError("create_collation() argument 1 must be str, not '%s'" % (type(name).__name__, ))
        if "\x00" in name:
            raise ValueError("embedded null character")

        if callback is None:
            del self.__collations[name]
            collation_callback = _ffi.NULL
        else:
            if not callable(callback):
                raise TypeError("parameter must be callable")

            @_ffi.callback("int(void*, int, const void*, int, const void*)")
            def collation_callback(context, len1, str1, len2, str2):
                text1 = _ffi.buffer(str1, len1)[:]
                text2 = _ffi.buffer(str2, len2)[:]
                try:
                    ret = callback(text1, text2)
                    assert isinstance(ret, (int, long))
                    return cmp(ret, 0)
                except Exception:
                    if _enable_callback_tracebacks[0]:
                        print(traceback.format_exc())
                    return 0

            self.__collations[name] = collation_callback

        if isinstance(name, unicode):
            name = name.encode('utf-8')
        ret = _lib.sqlite3_create_collation(self._db, name,
                                            _lib.SQLITE_UTF8,
                                            _ffi.NULL,
                                            collation_callback)
        if ret != _lib.SQLITE_OK:
            raise self._get_exception(ret)

    @_check_thread_wrap
    @_check_closed_wrap
    def set_authorizer(self, callback):
        """ Sets authorizer callback. """
        try:
            authorizer = self.__func_cache[callback]
        except KeyError:
            if callback is not None:
                @_ffi.callback("int(void*, int, const char*, const char*, "
                               "const char*, const char*)")
                def authorizer(userdata, action, arg1, arg2, dbname, source):
                    try:
                        ret = callback(action, arg1, arg2, dbname, source)
                        assert isinstance(ret, int)
                        # try to detect cases in which cffi would swallow
                        # OverflowError when casting the return value
                        assert int(_ffi.cast('int', ret)) == ret
                        return ret
                    except Exception as e:
                        print_or_clear_traceback(callback, e)
                        return _lib.SQLITE_DENY
                self.__func_cache[callback] = authorizer
            else:
                authorizer = _ffi.NULL

        ret = _lib.sqlite3_set_authorizer(self._db, authorizer, _ffi.NULL)
        if ret != _lib.SQLITE_OK:
            raise self._get_exception(ret)

    @_check_thread_wrap
    @_check_closed_wrap
    def set_progress_handler(self, callable, n):
        if callable is None:
            progress_handler = _ffi.NULL
        else:
            try:
                progress_handler = self.__func_cache[callable]
            except KeyError:
                @_ffi.callback("int(void*)")
                def progress_handler(userdata):
                    try:
                        return bool(callable())
                    except Exception as exc:
                        # abort query if error occurred
                        print_or_clear_traceback(callable, exc)
                        return 1
                self.__func_cache[callable] = progress_handler
        _lib.sqlite3_progress_handler(self._db, n, progress_handler,
                                      _ffi.NULL)

    @_check_thread_wrap
    @_check_closed_wrap
    def set_trace_callback(self, callable):
        if callable is None:
            trace_callback = _ffi.NULL
        else:
            try:
                trace_callback = self.__func_cache[callable]
            except KeyError:
                @_ffi.callback("int(unsigned, void*, void*, void*)")
                def trace_callback(typ, ctx, statement, sql):
                    if typ != _lib.SQLITE_TRACE_STMT:
                        return 0
                    expanded_sql = _lib.sqlite3_expanded_sql(statement)
                    if not expanded_sql:
                        exc = DataError("Expanded SQL string exceeds the maximum string length")
                        print_or_clear_traceback(self, exc)
                        stmt = _ffi.string(_ffi.cast('char*', sql)).decode('utf-8')
                    else:
                        try:
                            stmt = _ffi.string(expanded_sql).decode('utf-8')
                        finally:
                            _lib.sqlite3_free(expanded_sql)
                    try:
                        callable(stmt)
                    except Exception as exc:
                        print_or_clear_traceback(self, exc)
                    return 0
                self.__func_cache[callable] = trace_callback
        _lib.sqlite3_trace_v2(self._db, _lib.SQLITE_TRACE_STMT,
                              trace_callback, _ffi.NULL)

    @property
    @_check_closed_wrap
    def in_transaction(self):
        return not _lib.sqlite3_get_autocommit(self._db)

    def __get_total_changes(self):
        self._check_closed()
        return _lib.sqlite3_total_changes(self._db)
    total_changes = property(__get_total_changes)

    def __get_isolation_level(self):
        if not self.__initialized:
            raise ProgrammingError("Base Connection.__init__ not called")
        return self._isolation_level

    def __set_isolation_level(self, val):
        if val is None:
            self.commit()
            self._begin_statement = None
        else:
            if not isinstance(val, str):
                raise TypeError("isolation level must be " \
                        "a string or None, not %s" % type(val).__name__)
            stmt = str("BEGIN " + val).upper()
            if stmt not in BEGIN_STATMENTS:
                raise ValueError("isolation_level string must be '', 'DEFERRED', 'IMMEDIATE', or 'EXCLUSIVE'")
            self._begin_statement = stmt.encode('utf-8')
        self._isolation_level = val
    isolation_level = property(__get_isolation_level, __set_isolation_level)

    if hasattr(_lib, 'sqlite3_enable_load_extension'):
        @_check_thread_wrap
        @_check_closed_wrap
        def enable_load_extension(self, enabled):
            sys.audit("sqlite3.enable_load_extension", self, enabled)
            rc = _lib.sqlite3_enable_load_extension(self._db, int(enabled))
            if rc != _lib.SQLITE_OK:
                raise OperationalError("Error enabling load extension")

    if hasattr(_lib, 'sqlite3_backup_init'):
        def backup(self, target, *, pages=0, progress=None, name="main", sleep=0.250):
            """Makes a backup of the database. Non-standard."""
            if not isinstance(target, Connection):
                raise TypeError("target is not a Connection")
            if target == self:
                raise ValueError("target cannot be the same connection instance")
            if progress is not None and not callable(progress):
                raise TypeError("progress argument must be a callable")
            if pages == 0:
                pages = -1
            bck_conn = target._db
            if not bck_conn or not self._db:
                raise ProgrammingError("cannot operate on closed connection")
            self._check_closed()
            bck_handle = _lib.sqlite3_backup_init(bck_conn, b"main", self._db, name.encode("utf-8"))
            if not bck_handle:
                raise target._get_exception()
            while 1:
                rc = _lib.sqlite3_backup_step(bck_handle, pages)
                if progress:
                    try:
                        progress(rc, _lib.sqlite3_backup_remaining(bck_handle), _lib.sqlite3_backup_pagecount(bck_handle))
                    except:
                        _lib.sqlite3_backup_finish(bck_handle)
                        raise
                if rc == _lib.SQLITE_BUSY or rc == _lib.SQLITE_LOCKED:
                    _lib.sqlite3_sleep(sleep * 1000)
                elif rc == _lib.SQLITE_OK:
                    pass
                else:
                    break
            rc = _lib.sqlite3_backup_finish(bck_handle);
            if rc == _lib.SQLITE_OK:
                return None
            error = _lib.sqlite3_errstr(rc).decode("utf-8")
            raise OperationalError(error)

        @_check_thread_wrap
        @_check_closed_wrap
        def load_extension(self, ext_name):
            sys.audit("sqlite3.load_extension", self, ext_name)
            errmsg = _ffi.new('char **')
            ext_name_b = ext_name.encode()
            null = _ffi.cast('char *', 0)
            rc = _lib.sqlite3_load_extension(self._db, ext_name_b, null, errmsg)
            if rc != 0:
                raise OperationalError(_ffi.string(errmsg[0]).decode())


    @_check_thread_wrap
    @_check_closed_wrap
    def setlimit(self, category, limit):
        """
            category: int
                The limit category to be set.
            limit: int
                The new limit. If the new limit is a negative number, the limit is
                unchanged

        Set connection run-time limits.
        Attempts to increase a limit above its hard upper bound are silently truncated
        to the hard upper bound. Regardless of whether or not the limit was changed,
        the prior value of the limit is returned.
        """
        oldlimit = _lib.sqlite3_limit(self._db, category, limit)
        if oldlimit < 0:
            raise ProgrammingError("'category' is out of bounds");
        return oldlimit

    def getlimit(self, category):
        """
            category: int
                The limit category to be queried.

        Get connection run-time limits.
        """
        return self.setlimit(category, -1)

    @_check_thread_wrap
    @_check_closed_wrap
    def create_window_function(self, name, num_params, aggregate_class):
        """
            name: str
                The name of the SQL aggregate window function to be created or
                redefined.
            num_params: int
                The number of arguments the step and inverse methods takes.
            aggregate_class: object
                A class with step(), finalize(), value(), and inverse() methods.
                Set to None to clear the window function.

        Creates or redefines an aggregate window function. Non-standard.
        """
        try:
            (step_callback, final_callback,
                value_callback, inverse_callback) = self.__windows[aggregate_class]
        except KeyError:
            step_callback = self.__make_step_callback(aggregate_class)
            final_callback = self.__make_final_callback(aggregate_class)
            value_callback = self.__make_value_callback(aggregate_class)
            inverse_callback = self.__make_inverse_callback(aggregate_class)

            self.__windows[aggregate_class] = (
                step_callback, final_callback,
                value_callback, inverse_callback)

        if isinstance(name, unicode):
            name = name.encode('utf-8')
        ret = _lib.sqlite3_create_window_function(
            self._db, name, num_params,
            _lib.SQLITE_UTF8,
            _ffi.NULL,
            step_callback,
            final_callback,
            value_callback,
            inverse_callback,
            _ffi.NULL)
        if ret != _lib.SQLITE_OK:
            raise self._get_exception(ret)

    def __make_value_callback(self, cls):
        @_ffi.callback("void(sqlite3_context*)")
        def value_callback(context):
            res = _lib.sqlite3_aggregate_context(context,
                                                 _ffi.sizeof("size_t"))
            aggregate_ptr = _ffi.cast("size_t[1]", res)

            if not aggregate_ptr[0]:
                try:
                    aggregate = cls()
                except Exception as e:
                    msg = (b"user-defined aggregate's '__init__' "
                           b"method raised error")
                    set_sqlite_error(context, msg, e, unraisable_obj=cls)
                    return
                aggregate_id = id(aggregate)
                self.__aggregate_instances[aggregate_id] = aggregate
                aggregate_ptr[0] = aggregate_id
            else:
                aggregate = self.__aggregate_instances[aggregate_ptr[0]]

            try:
                meth = aggregate.value
            except AttributeError as e:
                msg = (b"user-defined aggregate's 'value' "
                       b"method not defined")
                set_sqlite_error(context, msg, e, unraisable_obj=cls)
            else:
                try:
                    val = meth()
                except Exception as e:
                    msg = (b"user-defined aggregate's 'value' "
                           b"method raised error")
                    set_sqlite_error(context, msg, e, unraisable_obj=cls)
                else:
                    try:
                        _convert_result(context, val)
                    except Exception as e:
                        msg = b"user-defined function raised exception"
                        set_sqlite_error(context, msg, e)
        return value_callback

    def __make_inverse_callback(self, cls):
        @_ffi.callback("void(sqlite3_context*, int, sqlite3_value**)")
        def inverse_callback(context, argc, c_params):
            res = _lib.sqlite3_aggregate_context(context,
                                                 _ffi.sizeof("size_t"))
            aggregate_ptr = _ffi.cast("size_t[1]", res)

            if not aggregate_ptr[0]:
                try:
                    aggregate = cls()
                except Exception as e:
                    msg = (b"user-defined aggregate's '__init__' "
                           b"method raised error")
                    set_sqlite_error(context, msg, e, unraisable_obj=cls)
                    return
                aggregate_id = id(aggregate)
                self.__aggregate_instances[aggregate_id] = aggregate
                aggregate_ptr[0] = aggregate_id
            else:
                aggregate = self.__aggregate_instances[aggregate_ptr[0]]

            try:
                meth = aggregate.inverse
            except AttributeError as e:
                msg = (b"user-defined aggregate's 'inverse' "
                       b"method not defined")
                set_sqlite_error(context, msg, e, unraisable_obj=cls)
            else:
                params = _convert_params(context, argc, c_params)
                try:
                    meth(*params)
                except Exception as e:
                    msg = (b"user-defined aggregate's 'inverse' "
                           b"method raised error")
                    set_sqlite_error(context, msg, e, unraisable_obj=cls)
        return inverse_callback

    if _sqlite_version_triple >= (3, 36, 0):
        @_check_thread_wrap
        @_check_closed_wrap
        def serialize(self, name="main"):
            """
                name: Which database to serialize.

            Serialize a database into a byte string.
            For an ordinary on-disk database file, the serialization is just a copy of the
            disk file. For an in-memory database or a "temp" database, the serialization is
            the same sequence of bytes which would be written to disk if that database
            were backed up to disk.
            """
            encname = name.encode('utf-8')
            flags = _lib.SQLITE_SERIALIZE_NOCOPY
            sizemem = _ffi.new('sqlite3_int64 *')
            data = _lib.sqlite3_serialize(self._db, encname, sizemem, flags)
            if data:
                return bytes(_ffi.buffer(data, sizemem[0]))
            flags &= ~_lib.SQLITE_SERIALIZE_NOCOPY
            data = _lib.sqlite3_serialize(self._db, encname, sizemem, flags)
            if not data:
                raise OperationalError("unable to serialize '%s'" % (name, ))
            try:
                return bytes(_ffi.buffer(data, sizemem[0]))
            finally:
                _lib.sqlite3_free(data)

        @_check_thread_wrap
        @_check_closed_wrap
        def deserialize(self, data, name="main"):
            """
                data:
                    The serialized database content.
                name: str = "main"
                    Which database to reopen with the deserialization.

            Load a serialized database.
            The deserialize interface causes the database connection to disconnect from the
            target database, and then reopen it as an in-memory database based on the given
            serialized data.
            The deserialize interface will fail with SQLITE_BUSY if the database is
            currently in a read transaction or is involved in a backup operation.
            """
            if isinstance(data, memoryview) and not data.c_contiguous:
                raise BufferError('only contiguous buffers are supported')
            if isinstance(data, list):
                raise TypeError("need bytes, not 'list'")
            size = len(data)
            buf = _lib.sqlite3_malloc64(size)
            if not buf:
                raise MemoryError()
            _ffi.memmove(buf, data, size)
            flags = _lib.SQLITE_DESERIALIZE_FREEONCLOSE | _lib.SQLITE_DESERIALIZE_RESIZEABLE
            rc = _lib.sqlite3_deserialize(self._db, name.encode('utf-8'), buf, size, size, flags)
            if rc != _lib.SQLITE_OK:
                raise self._get_exception(rc)

    @_check_closed_and_thread_wrap
    def blobopen(self, table, column, row, readonly=False, name='main'):
        """
            table: str
                Table name.
            column: str
                Column name.
            row: int
                Row index.
            readonly = False:
                Open the BLOB without write permissions.
            name: str = "main"
                Database name.

        Open and return a BLOB object.
        """
        blob_ref = _ffi.new("sqlite3_blob **")
        nameenc = name.encode('utf-8')
        tableenc = table.encode('utf-8')
        columnenc = column.encode('utf-8')
        rc = _lib.sqlite3_blob_open(
                self._db, nameenc, tableenc, columnenc,
                row, not readonly, blob_ref)
        if rc != _lib.SQLITE_OK:
            raise self._get_exception(rc)
        res = object.__new__(Blob)
        res.__init__(self, blob_ref[0])
        self.__blobs.append(weakref.ref(res))
        return res

    @_check_closed_and_thread_wrap
    def interrupt(self):
        """
        Abort any pending database operation.
        """
        _lib.sqlite3_interrupt(self._db)


class Cursor(object):
    __initialized = False
    __statement = None
    __locked = False

    def __init__(self, con):
        if self.__locked:
            raise ProgrammingError("Recursive use of cursors not allowed.")
        if not isinstance(con, Connection):
            raise TypeError
        self.__connection = con

        self.arraysize = 1
        self.row_factory = None
        self._reset = False
        self.__locked = False
        self.__closed = False
        self.__have_next_row = False
        self.__lastrowid = None
        self.__rowcount = -1

        con._check_thread()
        con._remember_cursor(self)

        # if a statement is in use by self, it's ._in_use_token is set to
        # self.__in_use_token. That way, we know whether the Statement is used
        # by *self* in self.__del__ and can only reset it in that case.
        self.__in_use_token = _InUseToken()
        self.__initialized = True

    def __del__(self):
        # Since statements are cached, they can outlive their parent cursor
        if self.__statement:
            self.__statement._reset(self.__in_use_token)

    def close(self):
        if not self.__initialized:
            raise ProgrammingError("Base Cursor.__init__ not called.")
        if self.__locked:
            raise ProgrammingError("Recursive use of cursors not allowed.")
        self.__connection._check_thread()
        self.__connection._check_closed()
        if self.__statement:
            self.__statement._reset(self.__in_use_token)
            self.__statement = None
        self.__closed = True

    def __check_cursor(self):
        if not self.__initialized:
            raise ProgrammingError("Base Cursor.__init__ not called.")
        if self.__closed:
            raise ProgrammingError("Cannot operate on a closed cursor.")
        if self.__locked:
            raise ProgrammingError("Recursive use of cursors not allowed.")
        self.__connection._check_thread()
        self.__connection._check_closed()

    def __check_cursor_wrap(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            self.__check_cursor()
            return func(self, *args, **kwargs)
        return wrapper

    def __check_reset(self):
        if self._reset:
            raise InterfaceError(
                "Cursor needed to be reset because of commit/rollback "
                "and can no longer be fetched from.")

    def __build_row_cast_map(self):
        if not self.__connection._detect_types:
            return
        self.__row_cast_map = []
        for i in xrange(_lib.sqlite3_column_count(self.__statement._statement)):
            converter = None

            if self.__connection._detect_types & PARSE_COLNAMES:
                colname = _lib.sqlite3_column_name(self.__statement._statement, i)
                if colname:
                    colname = _ffi.string(colname).decode('utf-8')
                    type_start = -1
                    key = None
                    for pos in range(len(colname)):
                        if colname[pos] == '[':
                            type_start = pos + 1
                        elif colname[pos] == ']' and type_start != -1:
                            key = colname[type_start:pos]
                            converter = converters[key.upper()]

            if converter is None and self.__connection._detect_types & PARSE_DECLTYPES:
                decltype = _lib.sqlite3_column_decltype(self.__statement._statement, i)
                if decltype:
                    decltype = _ffi.string(decltype).decode('utf-8')
                    # if multiple words, use first, eg.
                    # "INTEGER NOT NULL" => "INTEGER"
                    decltype = decltype.split()[0]
                    if '(' in decltype:
                        decltype = decltype[:decltype.index('(')]
                    converter = converters.get(decltype.upper(), None)

            self.__row_cast_map.append(converter)

    def __fetch_one_row(self):
        num_cols = _lib.sqlite3_data_count(self.__statement._statement)
        row = newlist_hint(num_cols)
        for i in xrange(num_cols):
            if self.__connection._detect_types:
                converter = self.__row_cast_map[i]
            else:
                converter = None

            if converter is not None:
                blob = _lib.sqlite3_column_blob(self.__statement._statement, i)
                if not blob:
                    val = None
                else:
                    blob_len = _lib.sqlite3_column_bytes(self.__statement._statement, i)
                    val = _ffi.buffer(blob, blob_len)[:]
                    val = converter(val)
            else:
                typ = _lib.sqlite3_column_type(self.__statement._statement, i)
                if typ == _lib.SQLITE_NULL:
                    val = None
                elif typ == _lib.SQLITE_INTEGER:
                    val = _lib.sqlite3_column_int64(self.__statement._statement, i)
                    val = int(val)
                elif typ == _lib.SQLITE_FLOAT:
                    val = _lib.sqlite3_column_double(self.__statement._statement, i)
                elif typ == _lib.SQLITE_TEXT:
                    text = _lib.sqlite3_column_text(self.__statement._statement, i)
                    text_len = _lib.sqlite3_column_bytes(self.__statement._statement, i)
                    val = _ffi.buffer(text, text_len)[:]
                    try:
                        val = self.__connection.text_factory(val)
                    except Exception:
                        column_name = _lib.sqlite3_column_name(
                            self.__statement._statement, i)
                        if column_name:
                            column_name = _ffi.string(column_name).decode('utf-8')
                        else:
                            column_name = "<unknown column name>"
                        val = val.decode('ascii', 'replace')
                        raise OperationalError(
                            "Could not decode to UTF-8 column '%s' with text '%s'" % (
                                column_name, val))
                elif typ == _lib.SQLITE_BLOB:
                    blob = _lib.sqlite3_column_blob(self.__statement._statement, i)
                    blob_len = _lib.sqlite3_column_bytes(self.__statement._statement, i)
                    val = _BLOB_TYPE(_ffi.buffer(blob, blob_len)[:])
            row.append(val)
        return tuple(row)

    def __execute(self, multiple, sql, many_params):
        self.__locked = True
        self._reset = False
        self.__have_next_row = False
        try:
            if not isinstance(sql, basestring):
                raise TypeError("operation parameter must be str or unicode, not %s" % (type(sql).__name__, ))
            try:
                del self.__description
            except AttributeError:
                pass
            self.__rowcount = -1
            if self.__statement:
                self.__statement._reset(self.__in_use_token)
            self.__statement = self.__connection._statement_cache.get(sql)

            if self.__connection._begin_statement and self.__statement._is_dml:
                if _lib.sqlite3_get_autocommit(self.__connection._db):
                    self.__connection._begin()

            for params in many_params:
                self.__statement._set_params(params, self.__in_use_token)

                # Actually execute the SQL statement

                ret = _lib.sqlite3_step(self.__statement._statement)

                # PyPy: if we get SQLITE_LOCKED, it's probably because
                # one of the cursors created previously is still alive
                # and not reset and the operation we're trying to do
                # makes Sqlite unhappy about that.  In that case, we
                # automatically reset all old cursors and try again.
                if ret == _lib.SQLITE_LOCKED:
                    self.__connection._reset_already_committed_statements()
                    ret = _lib.sqlite3_step(self.__statement._statement)

                if self.__statement._is_dml:
                    if self.__rowcount == -1:
                        self.__rowcount = 0
                    self.__rowcount += _lib.sqlite3_changes(self.__connection._db)
                else:
                    self.__rowcount = -1

                if not multiple:
                    self.__lastrowid = _lib.sqlite3_last_insert_rowid(self.__connection._db)

                if ret == _lib.SQLITE_ROW:
                    if multiple:
                        raise ProgrammingError("executemany() can only execute DML statements.")
                    self.__build_row_cast_map()
                    self.__have_next_row = True
                elif ret == _lib.SQLITE_DONE:
                    if not multiple:
                        self.__statement._reset(self.__in_use_token)
                else:
                    self.__statement._reset(self.__in_use_token)
                    raise self.__connection._get_exception(ret)

                if multiple:
                    self.__statement._reset(self.__in_use_token)
        finally:
            self.__locked = False
        return self

    @__check_cursor_wrap
    def execute(self, sql, params=[]):
        return self.__execute(False, sql, [params])

    @__check_cursor_wrap
    def executemany(self, sql, many_params):
        return self.__execute(True, sql, many_params)

    def executescript(self, sql):
        self.__check_cursor()
        self._reset = False
        if isinstance(sql, unicode):
            sql = sql.encode('utf-8')
        elif not isinstance(sql, str):
            raise TypeError("script argument must be unicode.")
        if len(sql) > _lib.sqlite3_limit(self.__connection._db, SQLITE_LIMIT_SQL_LENGTH, -1):
            raise DataError("query string is too large")
        if b'\x00' in sql:
            raise ValueError("the query contains a null character")
        statement_star = _ffi.new('sqlite3_stmt **')
        next_char = _ffi.new('char **')

        self.__connection.commit()
        while True:
            c_sql = _ffi.new("char[]", sql)
            rc = _lib.sqlite3_prepare(self.__connection._db, c_sql, -1,
                                      statement_star, next_char)
            if rc != _lib.SQLITE_OK:
                raise self.__connection._get_exception(rc)

            rc = _lib.SQLITE_ROW
            while rc == _lib.SQLITE_ROW:
                if not statement_star[0]:
                    rc = _lib.SQLITE_OK
                else:
                    rc = _lib.sqlite3_step(statement_star[0])

            if rc != _lib.SQLITE_DONE:
                _lib.sqlite3_finalize(statement_star[0])
                if rc == _lib.SQLITE_OK:
                    break
                else:
                    raise self.__connection._get_exception(rc)

            rc = _lib.sqlite3_finalize(statement_star[0])
            if rc != _lib.SQLITE_OK:
                raise self.__connection._get_exception(rc)

            sql = _ffi.string(next_char[0])
            if not sql:
                break
        return self

    def __iter__(self):
        return self

    def __next__(self):
        self.__check_cursor()
        self.__check_reset()
        if not self.__statement:
            raise StopIteration
        if not self.__have_next_row:
            raise StopIteration

        assert not self.__locked
        self.__locked = True
        try:
            next_row = self.__fetch_one_row()
        finally:
            self.__locked = False
        if self.row_factory is not None:
            next_row = self.row_factory(self, next_row)

        ret = _lib.sqlite3_step(self.__statement._statement)
        if ret == _lib.SQLITE_ROW:
            self.__have_next_row = True
        else:
            self.__have_next_row = False
            self.__statement._reset(self.__in_use_token)
            if ret != _lib.SQLITE_DONE:
                raise self.__connection._get_exception(ret)
        return next_row

    if sys.version_info[0] < 3:
        next = __next__
        del __next__

    def fetchone(self):
        return next(self, None)

    def fetchmany(self, size=None):
        if size is None:
            size = self.arraysize
        lst = []
        for row in self:
            lst.append(row)
            if len(lst) == size:
                break
        return lst

    def fetchall(self):
        return list(self)

    def __get_connection(self):
        self.__check_cursor()
        return self.__connection
    connection = property(__get_connection)

    def __get_rowcount(self):
        return self.__rowcount
    rowcount = property(__get_rowcount)

    def __get_description(self):
        try:
            return self.__description
        except AttributeError:
            if not self.__statement:
                return None
            statement = self.__statement
            if not statement._valid:
                return None

            numcols = _lib.sqlite3_column_count(statement._statement)
            if numcols <= 0:
                self.__description = None
                return None
            desc = []
            for i in xrange(numcols):
                name = _lib.sqlite3_column_name(statement._statement, i)
                if name:
                    name = _ffi.string(name).decode('utf-8')
                    if self.__connection._detect_types & PARSE_COLNAMES:
                        name = name.split("[", 1)[0].strip()
                desc.append((name, None, None, None, None, None, None))
            self.__description = tuple(desc)
            return self.__description
    description = property(__get_description)

    def __get_lastrowid(self):
        return self.__lastrowid
    lastrowid = property(__get_lastrowid)

    def setinputsizes(self, *args):
        pass

    def setoutputsize(self, *args):
        pass

class _InUseToken(object):
    __slots__ = ()

class Statement(object):
    _statement = None

    def __init__(self, connection, sql):
        self.__con = connection

        self._in_use_token = None

        if not isinstance(sql, basestring):
            raise TypeError("sql argument must be str, not %s" % (type(sql).__name__, ))
        if '\0' in sql:
            raise ProgrammingError("the query contains a null character")

        to_check = _sql_lstrip_comments(sql).upper()
        self._valid = bool(to_check)
        self._is_dml = to_check.startswith(('INSERT', 'UPDATE', 'DELETE', 'REPLACE'))

        statement_star = _ffi.new('sqlite3_stmt **')
        next_char = _ffi.new('char **')
        encoded = sql.encode('utf-8')
        if len(encoded) > _lib.sqlite3_limit(self.__con._db, SQLITE_LIMIT_SQL_LENGTH, -1):
            raise DataError("query string is too large")
        c_sql = _ffi.new("char[]", encoded)
        ret = _lib.sqlite3_prepare_v2(self.__con._db, c_sql, -1,
                                      statement_star, next_char)
        self._statement = statement_star[0]

        if ret == _lib.SQLITE_OK and not self._statement:
            # an empty statement, work around that, as it's the least trouble
            c_sql = _ffi.new("char[]", b"select 42 where 42 = 23")
            ret = _lib.sqlite3_prepare_v2(self.__con._db, c_sql, -1,
                                          statement_star, next_char)
            self._statement = statement_star[0]
            self._valid = False

        if ret != _lib.SQLITE_OK:
            raise self.__con._get_exception(ret)

        self.__con._remember_statement(self)

        tail = _ffi.string(next_char[0]).decode('utf-8')
        if _sql_lstrip_comments(tail):
            raise ProgrammingError("You can only execute one statement at a time.")

    def __new__(cls, *args):
        raise TypeError("cannot create '_sqlite3.Statement' instances")

    def __del__(self):
        if self._statement:
            self.__con._finalize_raw_statement(self._statement)

    def _finalize(self):
        if self._statement:
            self.__con._finalize_raw_statement(self._statement)
            self._statement = None
        self._in_use_token = None

    def _reset(self, token):
        assert isinstance(token, _InUseToken)
        if self._in_use_token is token and self._statement:
            _lib.sqlite3_reset(self._statement)
            self._in_use_token = None

    def _force_reset(self):
        if self._in_use_token and self._statement:
            _lib.sqlite3_reset(self._statement)
            self._in_use_token = None

    def __set_param(self, idx, param):
        typ = type(param)
        if BASE_TYPE_ADAPTED or (
            typ is not bytearray
            and typ is not bytes
            and typ is not float
            and typ is not int
            and typ is not str
            and typ is not NoneType
        ):
            param = _adapt(param)

        if param is None:
            rc = _lib.sqlite3_bind_null(self._statement, idx)
        elif isinstance(param, (bool, int, long)):
            if -2147483648 <= param <= 2147483647:
                rc = _lib.sqlite3_bind_int(self._statement, idx, param)
            else:
                try:
                    rc = _lib.sqlite3_bind_int64(self._statement, idx, param)
                except OverflowError:
                    raise OverflowError(
                        "Python int too large to convert to SQLite INTEGER"
                    )
        elif isinstance(param, float):
            rc = _lib.sqlite3_bind_double(self._statement, idx, param)
        elif isinstance(param, str):
            param = param.encode("utf-8")
            rc = _lib.sqlite3_bind_text(self._statement, idx, param,
                                        len(param), _SQLITE_TRANSIENT)
        elif isinstance(param, (buffer, bytes, bytearray)):
            if isinstance(param, buffer) and not param.c_contiguous:
                raise BufferError('underlying buffer is not C-contiguous')
            param = bytes(param)
            rc = _lib.sqlite3_bind_blob(self._statement, idx, param,
                                        len(param), _SQLITE_TRANSIENT)
        else:
            rc = _UNSUPPORTED_TYPE
        return rc

    def _set_params(self, params, token):
        assert isinstance(token, _InUseToken)
        self._in_use_token = token

        num_params_needed = _lib.sqlite3_bind_parameter_count(self._statement)
        if isinstance(params, (tuple, list)) or \
                not isinstance(params, dict) and \
                hasattr(params, '__getitem__'):
            try:
                num_params = len(params)
            except TypeError:
                num_params = -1
            if num_params != num_params_needed:
                raise ProgrammingError("Incorrect number of bindings supplied. "
                                       "The current statement uses %d, and "
                                       "there are %d supplied." %
                                       (num_params_needed, num_params))
            for i in range(num_params):
                rc = self.__set_param(i + 1, params[i])
                if rc is _UNSUPPORTED_TYPE:
                    raise ProgrammingError("Error binding parameter %d - "
                                           "Type '%s' is not supported." %
                                           (i, type(params[i]).__name__))
                if rc != _lib.SQLITE_OK:
                    raise self.__con._get_exception(rc)
        elif isinstance(params, dict):
            for i in range(1, num_params_needed + 1):
                param_name = _lib.sqlite3_bind_parameter_name(self._statement, i)
                if not param_name:
                    raise ProgrammingError("Binding %d has no name, but you "
                                           "supplied a dictionary (which has "
                                           "only names)." % i)
                param_name = _ffi.string(param_name).decode('utf-8')[1:]
                try:
                    param = params[param_name]
                except KeyError:
                    raise ProgrammingError("You did not supply a value for "
                                           "binding %d." % i)
                rc = self.__set_param(i, param)
                if rc is _UNSUPPORTED_TYPE:
                    raise ProgrammingError("Error binding parameter :%s - "
                                           "Type '%s' is not supported." %
                                           (param_name, type(param).__name__))
                if rc != _lib.SQLITE_OK:
                    raise self.__con._get_exception(rc)
        else:
            raise ProgrammingError("parameters are of unsupported type")


class Row(object):
    def __init__(self, cursor, values):
        if not (type(cursor) is Cursor or issubclass(type(cursor), Cursor)):
            raise TypeError("instance of cursor required for first argument")
        self.description = cursor.description
        self.values = values

    def __len__(self):
        return len(self.values)

    def __getitem__(self, item):
        if isinstance(item, (int, long)):
            return self.values[item]
        elif isinstance(item, slice):
            return self.values[item]
        elif isinstance(item, str):
            for idx, desc in enumerate(self.description):
                # but to bug compatibility: CPython does case folding only for
                # ascii chars
                if desc[0] == item:
                    return self.values[idx]
                if not desc[0].isascii() or not item.isascii():
                    continue
                if desc[0].lower() == item.lower():
                    return self.values[idx]
            raise IndexError("No item with that key")
        raise IndexError(f"index must be int or string, not '{type(item).__name__}'")

    def keys(self):
        return [desc[0] for desc in self.description]

    def __eq__(self, other):
        if not isinstance(other, Row):
            return NotImplemented
        if self.description != other.description:
            return False
        if self.values != other.values:
            return False
        return True

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash(tuple(self.description)) ^ hash(tuple(self.values))

_INT_MIN = -2**(struct.calcsize('i') * 8 - 1)
_INT_MAX = ~_INT_MIN

class Blob(object):
    def __new__(self, *args, **kwargs):
        raise TypeError("cannot create '_sqlite3.Blob' instances")

    def __init__(self, con, blob):
        if not isinstance(con, Connection):
            raise TypeError
        self.__connection = con
        self.__blob = blob
        self.__offset = 0

    def _check(self):
        self.__connection._check_closed()
        self.__connection._check_thread()
        if not self.__blob:
            raise ProgrammingError("Cannot operate on a closed blob")

    def close(self):
        """ Close the blob. """
        if self.__blob:
            _lib.sqlite3_blob_close(self.__blob)
            self.__blob = _ffi.NULL

    def read(self, length=-1):
        """
            length: int = -1
                Read length in bytes.

        Read data at the current offset position.
        If the end of the blob is reached, the data up to end of file will be returned.
        When length is not specified, or is negative, Blob.read() will read until the
        end of the blob.
        """
        self._check()
        # Make sure we never read past "EOB". Also read the rest of the blob if
        # a negative length is specified.
        blob_len = _lib.sqlite3_blob_bytes(self.__blob)
        max_read_len = blob_len - self.__offset
        if length < 0 or length > max_read_len:
            length = max_read_len
        buffer = self.__inner_read(length, self.__offset)
        self.__offset += length
        return buffer

    def __inner_read(self, length, offset):
        raw_buffer = _ffi.new("char[]", length)
        rc = _lib.sqlite3_blob_read(self.__blob, raw_buffer, length, offset)
        if rc != _lib.SQLITE_OK:
            raise self.__connection._get_exception(rc)
        return _ffi.buffer(raw_buffer, length)[:]

    def write(self, data):
        """
            data: Py_buffer

        Write data at the current offset.

        This function cannot change the blob length.  Writing beyond the end of the
        blob will result in an exception being raised.
        """
        self._check()
        self.__inner_write(data, self.__offset)
        self.__offset += len(data)

    def __inner_write(self, data, offset):
        blob_len = _lib.sqlite3_blob_bytes(self.__blob)
        remaining_len = blob_len - offset
        if len(data) > remaining_len:
            raise ValueError("data longer than blob length")
        rc = _lib.sqlite3_blob_write(self.__blob, _ffi.from_buffer(data),
                                     len(data), offset)
        if rc != _lib.SQLITE_OK:
            raise self.__connection._get_exception(rc)

    def seek(self, offset, origin=0):
        """
            offset: int
            origin: int = 0

        Set the current access position to offset.

        The origin argument defaults to os.SEEK_SET (absolute blob positioning).
        Other values for origin are os.SEEK_CUR (seek relative to the current position)
        and os.SEEK_END (seek relative to the blob's end).
        """
        self._check()
        blob_len = _lib.sqlite3_blob_bytes(self.__blob)
        offset = operator.index(offset)
        if origin == 0:
            pass
        elif origin == os.SEEK_CUR:
            offset += self.__offset
        elif origin == os.SEEK_END:
            offset += blob_len
        else:
            raise ValueError("'origin' should be os.SEEK_SET, os.SEEK_CUR, or "
                            "os.SEEK_END")
        if not 0 <= offset <= blob_len:
            if not _INT_MIN <= offset <= _INT_MAX:
                raise OverflowError('seek offset results in overflow')
            raise ValueError("offset out of blob range")
        self.__offset = offset

    def tell(self):
        """ Return the current access position for the blob."""
        self._check()
        return self.__offset

    def __getitem__(self, item):
        self._check()
        blob_len = _lib.sqlite3_blob_bytes(self.__blob)
        if isinstance(item, slice):
            start, stop, stride = item.indices(blob_len)
            length = len(range(start, stop, stride))
            if stride == 1:
                readlen = length
            else:
                readlen = stop - start
            raw_buffer = _ffi.new("char[]", readlen)
            rc = _lib.sqlite3_blob_read(self.__blob, raw_buffer, readlen, start)
            if rc != _lib.SQLITE_OK:
                raise self.__connection._get_exception(rc)
            return _ffi.buffer(raw_buffer, readlen)[::stride]
        else:
            offset = operator.index(item)
            if offset < 0:
                offset += blob_len
            if not 0 <= offset < blob_len:
                if offset > _INT_MAX:
                    raise IndexError("cannot fit 'int'")
                raise IndexError("index out of range")
            raw_buffer = _ffi.new("char[]", 1)
            rc = _lib.sqlite3_blob_read(self.__blob, raw_buffer, 1, offset)
            if rc != _lib.SQLITE_OK:
                raise self.__connection._get_exception(rc)
            return _ffi.buffer(raw_buffer, 1)[0][0]

    def __setitem__(self, item, value):
        self._check()
        blob_len = _lib.sqlite3_blob_bytes(self.__blob)
        if isinstance(item, slice):
            start, stop, stride = item.indices(blob_len)
            length = len(range(start, stop, stride))
            if length != len(value):
                raise IndexError("Blob slice assignment is wrong size")
            if stride == 1:
                rc = _lib.sqlite3_blob_write(self.__blob, _ffi.from_buffer(value),
                                             len(value), start)
                if rc != _lib.SQLITE_OK:
                    raise self.__connection._get_exception(rc)
            else:
                readlen = stop - start
                raw_buffer = _ffi.new("unsigned char[]", readlen)
                rc = _lib.sqlite3_blob_read(self.__blob, raw_buffer, readlen, start)
                if rc != _lib.SQLITE_OK:
                    raise self.__connection._get_exception(rc)
                # raw_buffer[0: readlen: stride] = value
                j = 0
                for i in range(0, readlen, stride):
                    raw_buffer[i] = value[j]
                    j += 1
                rc = _lib.sqlite3_blob_write(self.__blob, raw_buffer,
                                             readlen, start)
                if rc != _lib.SQLITE_OK:
                    raise self.__connection._get_exception(rc)
        else:
            offset = operator.index(item)
            value = operator.index(value)
            if offset < 0:
                offset += blob_len
            if not 0 <= offset < blob_len:
                raise IndexError("Blob index out of range")
            if not 0 <= value < 256:
                raise ValueError("byte must be in range(0, 256)")
            data = _ffi.new('unsigned char[1]')
            data[0] = value
            rc = _lib.sqlite3_blob_write(self.__blob, data, len(data), offset)
            if rc != _lib.SQLITE_OK:
                raise self.__connection._get_exception(rc)


    def __iter__(self):
        raise TypeError("blob is not iterable")

    def __enter__(self):
        self._check()
        return self

    def __exit__(self, typ, val, tb):
        self._check()
        self.close()
        return False

    def __len__(self):
        self._check()
        return _lib.sqlite3_blob_bytes(self.__blob)

def _sql_lstrip_comments(s):
    index = 0
    while index < len(s):
        char = s[index]
        index += 1
        if char in ' \t\f\n\r':
            continue
        elif char == '-':
            # skip line comment
            if index < len(s) and s[index] == '-':
                while index < len(s):
                    char = s[index]
                    index += 1
                    if char == '\n':
                        break
                if index == len(s):
                    return ''
                continue
        elif char == '/':
            # skip C-style comment
            if index < len(s) and s[index] == '*':
                while index < len(s):
                    char = s[index]
                    index += 1
                    if char == '*' and index < len(s) and s[index] == '/':
                        index += 1
                        break
                continue
        return s[index-1:]
    return ''


def _convert_params(con, nargs, params):
    _params = []
    for i in range(nargs):
        typ = _lib.sqlite3_value_type(params[i])
        if typ == _lib.SQLITE_NULL:
            val = None
        elif typ == _lib.SQLITE_INTEGER:
            val = _lib.sqlite3_value_int64(params[i])
            val = int(val)
        elif typ == _lib.SQLITE_FLOAT:
            val = _lib.sqlite3_value_double(params[i])
        elif typ == _lib.SQLITE_TEXT:
            val = _lib.sqlite3_value_text(params[i])
            length = _lib.sqlite3_value_bytes(params[i])
            val = _ffi.buffer(val, length)[:].decode('utf-8')
        elif typ == _lib.SQLITE_BLOB:
            blob = _lib.sqlite3_value_blob(params[i])
            blob_len = _lib.sqlite3_value_bytes(params[i])
            val = _BLOB_TYPE(_ffi.buffer(blob, blob_len)[:])
        else:
            raise NotImplementedError
        _params.append(val)
    return _params


def _convert_result(con, val):
    if val is None:
        _lib.sqlite3_result_null(con)
    elif isinstance(val, (bool, int, long)):
        _lib.sqlite3_result_int64(con, int(val))
    elif isinstance(val, float):
        _lib.sqlite3_result_double(con, val)
    elif isinstance(val, str):
        val = val.encode('utf-8')
        _lib.sqlite3_result_text(con, val, len(val), _SQLITE_TRANSIENT)
    elif isinstance(val, (buffer, bytes)):
        if isinstance(val, buffer) and not val.c_contiguous:
            raise BufferError('underlying buffer is not C-contiguous')
        _lib.sqlite3_result_blob(con, bytes(val), len(val), _SQLITE_TRANSIENT)
    else:
        raise NotImplementedError

def set_sqlite_error(context, msg, exc, unraisable_obj=None):
    """internal function to set sqlite3 error and maybe raise an exception
       msg is bytes
    """
    if isinstance(exc, MemoryError):
        _lib.sqlite3_result_error_nomem(context)
    elif isinstance(exc, OverflowError):
        _lib.sqlite3_result_error_toobig(context)
    else:
        _lib.sqlite3_result_error(context, msg, len(msg))
    if unraisable_obj is None:
        unraisable_obj = context
    print_or_clear_traceback(unraisable_obj, exc)

def print_or_clear_traceback(ctx, exc):
    """the function name matches CPython, but the functionality is a bit
    different: there is no need to clear the excption
    """
    if _enable_callback_tracebacks[0]:
        import __pypy__
        try:
            __pypy__.write_unraisable('in sqlite3 callback', exc, ctx)
        except Exception as e:
            # Should never happen
            print(e, file=sys.stderr)

def _function_callback(real_cb, context, nargs, c_params):
    params = _convert_params(context, nargs, c_params)
    try:
        val = real_cb(*params)
    except Exception as e:
        msg = b"user-defined function raised exception"
        set_sqlite_error(context, msg, e, unraisable_obj=real_cb)
    else:
        try:
            _convert_result(context, val)
        except Exception as e:
            msg = b"user-defined function raised exception"
            set_sqlite_error(context, msg, e, unraisable_obj=real_cb)

converters = {}
adapters = {}
_enable_callback_tracebacks = [0]


class PrepareProtocol(object):
    pass


def register_adapter(typ, callable):
    global BASE_TYPE_ADAPTED

    if typ in BASE_TYPES:
        BASE_TYPE_ADAPTED = True

    adapters[typ, PrepareProtocol] = callable


def register_converter(name, callable):
    converters[name.upper()] = callable


def register_adapters_and_converters():
    def adapt_date(val):
        return val.isoformat()

    def adapt_datetime(val):
        return val.isoformat(" ")

    def convert_date(val):
        return datetime.date(*map(int, val.split("-")))

    def convert_timestamp(val):
        datepart, timepart = val.split(" ")
        year, month, day = map(int, datepart.split("-"))
        timepart_full = timepart.split(".")
        hours, minutes, seconds = map(int, timepart_full[0].split(":"))
        if len(timepart_full) == 2:
            microseconds = int(timepart_full[1])
        else:
            microseconds = 0
        return datetime.datetime(year, month, day, hours, minutes, seconds,
                                 microseconds)

    register_adapter(datetime.date, adapt_date)
    register_adapter(datetime.datetime, adapt_datetime)
    register_converter("date", convert_date)
    register_converter("timestamp", convert_timestamp)


SENTINEL = object()

def adapt(val, proto=PrepareProtocol, alt=SENTINEL):
    return _adapt(val, proto, alt, raise_=True)

def _adapt(val, proto=PrepareProtocol, alt=SENTINEL, raise_=False):
    # look for an adapter in the registry
    adapter = adapters.get((type(val), proto), None)
    if adapter is not None:
        return adapter(val)

    # try to have the protocol adapt this object
    if hasattr(proto, '__adapt__'):
        try:
            adapted = proto.__adapt__(val)
        except TypeError:
            pass
        else:
            if adapted is not None:
                return adapted

    # and finally try to have the object adapt itself
    if hasattr(val, '__conform__'):
        try:
            adapted = val.__conform__(proto)
        except TypeError:
            pass
        else:
            if adapted is not None:
                return adapted
    if alt is not SENTINEL:
        return alt
    if raise_:
        raise ProgrammingError("can't adapt")
    return val

def enable_shared_cache(enable):
    raise OperationalError("enable_shared_cache not supported on PyPy (and it's deprecated anyway)")

def complete_statement(statement=None):
    """Checks if a string contains a complete SQL statement.
    """
    if not statement:
        raise TypeError("complete_statement missing required argument 'statement' (pos 1)")
    if not isinstance(statement, str):
        raise TypeError(f"complete_statement() argument 'statement' must be str, not {type(statement)}")
    ret = _lib.sqlite3_complete(statement.encode('utf-8'))
    return bool(ret)

def enable_callback_tracebacks(enable, /):
    """Enable or disable callback functions throwing errors to stderr.
    """
    _enable_callback_tracebacks[0] = int(enable)


register_adapters_and_converters()

threadsafety = [0, 3, 1][_lib.sqlite3_threadsafe()]

