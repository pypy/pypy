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

from ctypes import c_void_p, c_int, c_double, c_int64, c_char_p, c_char, cdll
from ctypes import POINTER, byref, string_at, CFUNCTYPE, cast
from ctypes import sizeof, c_ssize_t
from collections import OrderedDict
from functools import wraps
import datetime
import sys
import weakref
from threading import _get_ident as _thread_get_ident

names = "sqlite3.dll libsqlite3.so.0 libsqlite3.so libsqlite3.dylib".split()
for name in names:
    try:
        sqlite = cdll.LoadLibrary(name)
        break
    except OSError:
        continue
else:
    raise ImportError("Could not load C-library, tried: %s" % (names,))

# pysqlite version information
version = "2.6.0"

# pysqlite constants
PARSE_COLNAMES = 1
PARSE_DECLTYPES = 2

##########################################
# BEGIN Wrapped SQLite C API and constants
##########################################

SQLITE_OK = 0
SQLITE_ERROR = 1
SQLITE_INTERNAL = 2
SQLITE_PERM = 3
SQLITE_ABORT = 4
SQLITE_BUSY = 5
SQLITE_LOCKED = 6
SQLITE_NOMEM = 7
SQLITE_READONLY = 8
SQLITE_INTERRUPT = 9
SQLITE_IOERR = 10
SQLITE_CORRUPT = 11
SQLITE_NOTFOUND = 12
SQLITE_FULL = 13
SQLITE_CANTOPEN = 14
SQLITE_PROTOCOL = 15
SQLITE_EMPTY = 16
SQLITE_SCHEMA = 17
SQLITE_TOOBIG = 18
SQLITE_CONSTRAINT = 19
SQLITE_MISMATCH = 20
SQLITE_MISUSE = 21
SQLITE_NOLFS = 22
SQLITE_AUTH = 23
SQLITE_FORMAT = 24
SQLITE_RANGE = 25
SQLITE_NOTADB = 26
SQLITE_ROW = 100
SQLITE_DONE = 101
SQLITE_INTEGER = 1
SQLITE_FLOAT = 2
SQLITE_BLOB = 4
SQLITE_NULL = 5
SQLITE_TEXT = 3
SQLITE3_TEXT = 3

SQLITE_TRANSIENT = cast(-1, c_void_p)
SQLITE_UTF8 = 1

SQLITE_DENY     = 1
SQLITE_IGNORE   = 2

SQLITE_CREATE_INDEX             = 1
SQLITE_CREATE_TABLE             = 2
SQLITE_CREATE_TEMP_INDEX        = 3
SQLITE_CREATE_TEMP_TABLE        = 4
SQLITE_CREATE_TEMP_TRIGGER      = 5
SQLITE_CREATE_TEMP_VIEW         = 6
SQLITE_CREATE_TRIGGER           = 7
SQLITE_CREATE_VIEW              = 8
SQLITE_DELETE                   = 9
SQLITE_DROP_INDEX               = 10
SQLITE_DROP_TABLE               = 11
SQLITE_DROP_TEMP_INDEX          = 12
SQLITE_DROP_TEMP_TABLE          = 13
SQLITE_DROP_TEMP_TRIGGER        = 14
SQLITE_DROP_TEMP_VIEW           = 15
SQLITE_DROP_TRIGGER             = 16
SQLITE_DROP_VIEW                = 17
SQLITE_INSERT                   = 18
SQLITE_PRAGMA                   = 19
SQLITE_READ                     = 20
SQLITE_SELECT                   = 21
SQLITE_TRANSACTION              = 22
SQLITE_UPDATE                   = 23
SQLITE_ATTACH                   = 24
SQLITE_DETACH                   = 25
SQLITE_ALTER_TABLE              = 26
SQLITE_REINDEX                  = 27
SQLITE_ANALYZE                  = 28
SQLITE_CREATE_VTABLE            = 29
SQLITE_DROP_VTABLE              = 30
SQLITE_FUNCTION                 = 31

# SQLite C API

sqlite.sqlite3_value_int.argtypes = [c_void_p]
sqlite.sqlite3_value_int.restype = c_int

sqlite.sqlite3_value_int64.argtypes = [c_void_p]
sqlite.sqlite3_value_int64.restype = c_int64

sqlite.sqlite3_value_blob.argtypes = [c_void_p]
sqlite.sqlite3_value_blob.restype = c_void_p

sqlite.sqlite3_value_bytes.argtypes = [c_void_p]
sqlite.sqlite3_value_bytes.restype = c_int

sqlite.sqlite3_value_double.argtypes = [c_void_p]
sqlite.sqlite3_value_double.restype = c_double

sqlite.sqlite3_value_text.argtypes = [c_void_p]
sqlite.sqlite3_value_text.restype = c_char_p

sqlite.sqlite3_value_type.argtypes = [c_void_p]
sqlite.sqlite3_value_type.restype = c_int

sqlite.sqlite3_bind_blob.argtypes = [c_void_p, c_int, c_void_p, c_int, c_void_p]
sqlite.sqlite3_bind_blob.restype = c_int
sqlite.sqlite3_bind_double.argtypes = [c_void_p, c_int, c_double]
sqlite.sqlite3_bind_double.restype = c_int
sqlite.sqlite3_bind_int.argtypes = [c_void_p, c_int, c_int]
sqlite.sqlite3_bind_int.restype = c_int
sqlite.sqlite3_bind_int64.argtypes = [c_void_p, c_int, c_int64]
sqlite.sqlite3_bind_int64.restype = c_int
sqlite.sqlite3_bind_null.argtypes = [c_void_p, c_int]
sqlite.sqlite3_bind_null.restype = c_int
sqlite.sqlite3_bind_parameter_count.argtypes = [c_void_p]
sqlite.sqlite3_bind_parameter_count.restype = c_int
sqlite.sqlite3_bind_parameter_index.argtypes = [c_void_p, c_char_p]
sqlite.sqlite3_bind_parameter_index.restype = c_int
sqlite.sqlite3_bind_parameter_name.argtypes = [c_void_p, c_int]
sqlite.sqlite3_bind_parameter_name.restype = c_char_p
sqlite.sqlite3_bind_text.argtypes = [c_void_p, c_int, c_char_p, c_int, c_void_p]
sqlite.sqlite3_bind_text.restype = c_int
sqlite.sqlite3_busy_timeout.argtypes = [c_void_p, c_int]
sqlite.sqlite3_busy_timeout.restype = c_int
sqlite.sqlite3_changes.argtypes = [c_void_p]
sqlite.sqlite3_changes.restype = c_int
sqlite.sqlite3_close.argtypes = [c_void_p]
sqlite.sqlite3_close.restype = c_int
sqlite.sqlite3_column_blob.argtypes = [c_void_p, c_int]
sqlite.sqlite3_column_blob.restype = c_void_p
sqlite.sqlite3_column_bytes.argtypes = [c_void_p, c_int]
sqlite.sqlite3_column_bytes.restype = c_int
sqlite.sqlite3_column_count.argtypes = [c_void_p]
sqlite.sqlite3_column_count.restype = c_int
sqlite.sqlite3_column_decltype.argtypes = [c_void_p, c_int]
sqlite.sqlite3_column_decltype.restype = c_char_p
sqlite.sqlite3_column_double.argtypes = [c_void_p, c_int]
sqlite.sqlite3_column_double.restype = c_double
sqlite.sqlite3_column_int64.argtypes = [c_void_p, c_int]
sqlite.sqlite3_column_int64.restype = c_int64
sqlite.sqlite3_column_name.argtypes = [c_void_p, c_int]
sqlite.sqlite3_column_name.restype = c_char_p
sqlite.sqlite3_column_text.argtypes = [c_void_p, c_int]
sqlite.sqlite3_column_text.restype = POINTER(c_char)
sqlite.sqlite3_column_type.argtypes = [c_void_p, c_int]
sqlite.sqlite3_column_type.restype = c_int
sqlite.sqlite3_complete.argtypes = [c_char_p]
sqlite.sqlite3_complete.restype = c_int
sqlite.sqlite3_errcode.restype = c_int
sqlite.sqlite3_errmsg.argtypes = [c_void_p]
sqlite.sqlite3_errmsg.restype = c_char_p
sqlite.sqlite3_finalize.argtypes = [c_void_p]
sqlite.sqlite3_finalize.restype = c_int
sqlite.sqlite3_get_autocommit.argtypes = [c_void_p]
sqlite.sqlite3_get_autocommit.restype = c_int
sqlite.sqlite3_last_insert_rowid.argtypes = [c_void_p]
sqlite.sqlite3_last_insert_rowid.restype = c_int64
sqlite.sqlite3_libversion.argtypes = []
sqlite.sqlite3_libversion.restype = c_char_p
sqlite.sqlite3_open.argtypes = [c_char_p, c_void_p]
sqlite.sqlite3_open.restype = c_int
sqlite.sqlite3_prepare.argtypes = [c_void_p, c_char_p, c_int, c_void_p, POINTER(c_char_p)]
sqlite.sqlite3_prepare.restype = c_int
sqlite.sqlite3_prepare_v2.argtypes = [c_void_p, c_char_p, c_int, c_void_p, POINTER(c_char_p)]
sqlite.sqlite3_prepare_v2.restype = c_int
sqlite.sqlite3_step.argtypes = [c_void_p]
sqlite.sqlite3_step.restype = c_int
sqlite.sqlite3_reset.argtypes = [c_void_p]
sqlite.sqlite3_reset.restype = c_int
sqlite.sqlite3_total_changes.argtypes = [c_void_p]
sqlite.sqlite3_total_changes.restype = c_int

sqlite.sqlite3_result_blob.argtypes = [c_void_p, c_char_p, c_int, c_void_p]
sqlite.sqlite3_result_blob.restype = None
sqlite.sqlite3_result_int64.argtypes = [c_void_p, c_int64]
sqlite.sqlite3_result_int64.restype = None
sqlite.sqlite3_result_null.argtypes = [c_void_p]
sqlite.sqlite3_result_null.restype = None
sqlite.sqlite3_result_double.argtypes = [c_void_p, c_double]
sqlite.sqlite3_result_double.restype = None
sqlite.sqlite3_result_error.argtypes = [c_void_p, c_char_p, c_int]
sqlite.sqlite3_result_error.restype = None
sqlite.sqlite3_result_text.argtypes = [c_void_p, c_char_p, c_int, c_void_p]
sqlite.sqlite3_result_text.restype = None

_HAS_LOAD_EXTENSION = hasattr(sqlite, "sqlite3_enable_load_extension")
if _HAS_LOAD_EXTENSION:
    sqlite.sqlite3_enable_load_extension.argtypes = [c_void_p, c_int]
    sqlite.sqlite3_enable_load_extension.restype = c_int

##########################################
# END Wrapped SQLite C API and constants
##########################################

# SQLite version information
sqlite_version = sqlite.sqlite3_libversion()

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

def connect(database, **kwargs):
    factory = kwargs.get("factory", Connection)
    return factory(database, **kwargs)

def unicode_text_factory(x):
    return unicode(x, 'utf-8')


class _StatementCache(object):
    def __init__(self, connection, maxcount):
        self.connection = connection
        self.maxcount = maxcount
        self.cache = OrderedDict()

    def get(self, sql, row_factory):
        if isinstance(sql, unicode):
            sql = sql.encode('utf-8')

        try:
            stat = self.cache[sql]
        except KeyError:
            stat = Statement(self.connection, sql)
            self.cache[sql] = stat
            if len(self.cache) > self.maxcount:
                self.cache.popitem(0)

        if stat._in_use:
            stat = Statement(self.connection, sql)
        stat._row_factory = row_factory
        return stat


class Connection(object):
    __initialized = False
    _db = None

    def __init__(self, database, timeout=5.0, detect_types=0, isolation_level="",
                 check_same_thread=True, factory=None, cached_statements=100):
        self.__initialized = True
        self._db = c_void_p()

        if sqlite.sqlite3_open(database, byref(self._db)) != SQLITE_OK:
            raise OperationalError("Could not open database")
        if timeout is not None:
            timeout = int(timeout * 1000)  # pysqlite2 uses timeout in seconds
            sqlite.sqlite3_busy_timeout(self._db, timeout)

        self.row_factory = None
        self.text_factory = unicode_text_factory

        self._detect_types = detect_types
        self._in_transaction = False
        self.isolation_level = isolation_level

        self._cursors = []
        self.__statements = []
        self.__statement_counter = 0
        self._statement_cache = _StatementCache(self, cached_statements)

        self.__func_cache = {}
        self.__aggregates = {}
        self.__aggregate_instances = {}
        self.__collations = {}
        if check_same_thread:
            self.__thread_ident = _thread_get_ident()

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

    def __del__(self):
        if self._db:
            sqlite.sqlite3_close(self._db)

    def close(self):
        self._check_thread()

        for statement in self.__statements:
            obj = statement()
            if obj is not None:
                obj._finalize()

        if self._db:
            ret = sqlite.sqlite3_close(self._db)
            if ret != SQLITE_OK:
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
            if self.__thread_ident == _thread_get_ident():
                return
        except AttributeError:
            pass
        else:
            raise ProgrammingError(
                "SQLite objects created in a thread can only be used in that same thread."
                "The object was created in thread id %d and this is thread id %d",
                self.__thread_ident, _thread_get_ident())

    def _check_thread_wrap(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            self._check_thread()
            return func(self, *args, **kwargs)
        return wrapper

    def _get_exception(self, error_code=None):
        if error_code is None:
            error_code = sqlite.sqlite3_errcode(self._db)
        error_message = sqlite.sqlite3_errmsg(self._db)

        if error_code == SQLITE_OK:
            raise ValueError("error signalled but got SQLITE_OK")
        elif error_code in (SQLITE_INTERNAL, SQLITE_NOTFOUND):
            exc = InternalError
        elif error_code == SQLITE_NOMEM:
            exc = MemoryError
        elif error_code in (SQLITE_ERROR, SQLITE_PERM, SQLITE_ABORT, SQLITE_BUSY, SQLITE_LOCKED,
                SQLITE_READONLY, SQLITE_INTERRUPT, SQLITE_IOERR, SQLITE_FULL, SQLITE_CANTOPEN,
                SQLITE_PROTOCOL, SQLITE_EMPTY, SQLITE_SCHEMA):
            exc = OperationalError
        elif error_code == SQLITE_CORRUPT:
            exc = DatabaseError
        elif error_code == SQLITE_TOOBIG:
            exc = DataError
        elif error_code in (SQLITE_CONSTRAINT, SQLITE_MISMATCH):
            exc = IntegrityError
        elif error_code == SQLITE_MISUSE:
            exc = ProgrammingError
        else:
            exc = DatabaseError
        exc = exc(error_message)
        exc.error_code = error_code
        return exc

    def _remember_statement(self, statement):
        self.__statements.append(weakref.ref(statement))
        self.__statement_counter += 1

        if self.__statement_counter % 100 == 0:
            self.__statements = [ref for ref in self.__statements if ref() is not None]

    @_check_thread_wrap
    @_check_closed_wrap
    def __call__(self, sql):
        if not isinstance(sql, (str, unicode)):
            raise Warning("SQL is of wrong type. Must be string or unicode.")
        return self._statement_cache.get(sql, self.row_factory)

    def cursor(self, factory=None):
        self._check_thread()
        self._check_closed()
        if factory is None:
            factory = Cursor
        cur = factory(self)
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
        return _iterdump(self)

    def _begin(self):
        statement = c_void_p()
        next_char = c_char_p()
        ret = sqlite.sqlite3_prepare_v2(self._db, self.__begin_statement, -1,
                                        byref(statement), next_char)
        try:
            if ret != SQLITE_OK:
                raise self._get_exception(ret)
            ret = sqlite.sqlite3_step(statement)
            if ret != SQLITE_DONE:
                raise self._get_exception(ret)
            self._in_transaction = True
        finally:
            sqlite.sqlite3_finalize(statement)

    def commit(self):
        self._check_thread()
        self._check_closed()
        if not self._in_transaction:
            return

        for statement in self.__statements:
            obj = statement()
            if obj is not None:
                obj._reset()

        statement = c_void_p()
        next_char = c_char_p()
        ret = sqlite.sqlite3_prepare_v2(self._db, "COMMIT", -1,
                                        byref(statement), next_char)
        try:
            if ret != SQLITE_OK:
                raise self._get_exception(ret)
            ret = sqlite.sqlite3_step(statement)
            if ret != SQLITE_DONE:
                raise self._get_exception(ret)
            self._in_transaction = False
        finally:
            sqlite.sqlite3_finalize(statement)

    def rollback(self):
        self._check_thread()
        self._check_closed()
        if not self._in_transaction:
            return

        for statement in self.__statements:
            obj = statement()
            if obj is not None:
                obj._reset()

        for cursor_ref in self._cursors:
            cursor = cursor_ref()
            if cursor:
                cursor._reset = True

        statement = c_void_p()
        next_char = c_char_p()
        ret = sqlite.sqlite3_prepare_v2(self._db, "ROLLBACK", -1,
                                        byref(statement), next_char)
        try:
            if ret != SQLITE_OK:
                raise self._get_exception(ret)
            ret = sqlite.sqlite3_step(statement)
            if ret != SQLITE_DONE:
                raise self._get_exception(ret)
            self._in_transaction = False
        finally:
            sqlite.sqlite3_finalize(statement)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if exc_type is None and exc_value is None and exc_tb is None:
            self.commit()
        else:
            self.rollback()

    @_check_thread_wrap
    @_check_closed_wrap
    def create_function(self, name, num_args, callback):
        try:
            c_closure, _ = self.__func_cache[callback]
        except KeyError:
            def closure(context, nargs, c_params):
                function_callback(callback, context, nargs, c_params)
            c_closure = _FUNC(closure)
            self.__func_cache[callback] = c_closure, closure
        ret = sqlite.sqlite3_create_function(self._db, name, num_args,
                                             SQLITE_UTF8, None,
                                             c_closure,
                                             cast(None, _STEP),
                                             cast(None, _FINAL))
        if ret != SQLITE_OK:
            raise self.OperationalError("Error creating function")

    @_check_thread_wrap
    @_check_closed_wrap
    def create_aggregate(self, name, num_args, cls):
        try:
            c_step_callback, c_final_callback, _, _ = self.__aggregates[cls]
        except KeyError:
            def step_callback(context, argc, c_params):

                aggregate_ptr = cast(
                    sqlite.sqlite3_aggregate_context(
                        context, sizeof(c_ssize_t)),
                    POINTER(c_ssize_t))

                if not aggregate_ptr[0]:
                    try:
                        aggregate = cls()
                    except Exception:
                        msg = ("user-defined aggregate's '__init__' "
                               "method raised error")
                        sqlite.sqlite3_result_error(context, msg, len(msg))
                        return
                    aggregate_id = id(aggregate)
                    self.__aggregate_instances[aggregate_id] = aggregate
                    aggregate_ptr[0] = aggregate_id
                else:
                    aggregate = self.__aggregate_instances[aggregate_ptr[0]]

                params = _convert_params(context, argc, c_params)
                try:
                    aggregate.step(*params)
                except Exception:
                    msg = ("user-defined aggregate's 'step' "
                           "method raised error")
                    sqlite.sqlite3_result_error(context, msg, len(msg))

            def final_callback(context):

                aggregate_ptr = cast(
                    sqlite.sqlite3_aggregate_context(
                        context, sizeof(c_ssize_t)),
                    POINTER(c_ssize_t))

                if aggregate_ptr[0]:
                    aggregate = self.__aggregate_instances[aggregate_ptr[0]]
                    try:
                        val = aggregate.finalize()
                    except Exception:
                        msg = ("user-defined aggregate's 'finalize' "
                               "method raised error")
                        sqlite.sqlite3_result_error(context, msg, len(msg))
                    else:
                        _convert_result(context, val)
                    finally:
                        del self.__aggregate_instances[aggregate_ptr[0]]

            c_step_callback = _STEP(step_callback)
            c_final_callback = _FINAL(final_callback)

            self.__aggregates[cls] = (c_step_callback, c_final_callback,
                                     step_callback, final_callback)

        ret = sqlite.sqlite3_create_function(self._db, name, num_args,
                                             SQLITE_UTF8, None,
                                             cast(None, _FUNC),
                                             c_step_callback,
                                             c_final_callback)
        if ret != SQLITE_OK:
            raise self._get_exception(ret)

    @_check_thread_wrap
    @_check_closed_wrap
    def create_collation(self, name, callback):
        name = name.upper()
        if not name.replace('_', '').isalnum():
            raise ProgrammingError("invalid character in collation name")

        if callback is None:
            del self.__collations[name]
            c_collation_callback = cast(None, _COLLATION)
        else:
            if not callable(callback):
                raise TypeError("parameter must be callable")

            def collation_callback(context, len1, str1, len2, str2):
                text1 = string_at(str1, len1)
                text2 = string_at(str2, len2)

                return callback(text1, text2)

            c_collation_callback = _COLLATION(collation_callback)
            self.__collations[name] = c_collation_callback

        ret = sqlite.sqlite3_create_collation(self._db, name,
                                              SQLITE_UTF8,
                                              None,
                                              c_collation_callback)
        if ret != SQLITE_OK:
            raise self._get_exception(ret)

    @_check_thread_wrap
    @_check_closed_wrap
    def set_authorizer(self, callback):
        try:
            c_authorizer, _ = self.__func_cache[callback]
        except KeyError:
            def authorizer(userdata, action, arg1, arg2, dbname, source):
                try:
                    return int(callback(action, arg1, arg2, dbname, source))
                except Exception:
                    return SQLITE_DENY
            c_authorizer = _AUTHORIZER(authorizer)

            self.__func_cache[callback] = c_authorizer, authorizer

        ret = sqlite.sqlite3_set_authorizer(self._db,
                                            c_authorizer,
                                            None)
        if ret != SQLITE_OK:
            raise self._get_exception(ret)

    @_check_thread_wrap
    @_check_closed_wrap
    def set_progress_handler(self, callable, nsteps):
        if callable is None:
            c_progress_handler = cast(None, _PROGRESS)
        else:
            try:
                c_progress_handler, _ = self.__func_cache[callable]
            except KeyError:
                def progress_handler(userdata):
                    try:
                        ret = callable()
                        return bool(ret)
                    except Exception:
                        # abort query if error occurred
                        return 1
                c_progress_handler = _PROGRESS(progress_handler)

                self.__func_cache[callable] = c_progress_handler, progress_handler
        ret = sqlite.sqlite3_progress_handler(self._db, nsteps,
                                              c_progress_handler,
                                              None)
        if ret != SQLITE_OK:
            raise self._get_exception(ret)

    def __get_total_changes(self):
        self._check_closed()
        return sqlite.sqlite3_total_changes(self._db)
    total_changes = property(__get_total_changes)

    def __get_isolation_level(self):
        return self._isolation_level

    def __set_isolation_level(self, val):
        if val is None:
            self.commit()
        else:
            if isinstance(val, unicode):
                val = str(val)
            self.__begin_statement = 'BEGIN ' + val
        self._isolation_level = val
    isolation_level = property(__get_isolation_level, __set_isolation_level)

    if _HAS_LOAD_EXTENSION:
        @_check_thread_wrap
        @_check_closed_wrap
        def enable_load_extension(self, enabled):
            rc = sqlite.sqlite3_enable_load_extension(self._db, int(enabled))
            if rc != SQLITE_OK:
                raise OperationalError("Error enabling load extension")


class Cursor(object):
    __initialized = False
    __connection = None
    __statement = None

    def __init__(self, con):
        self.__initialized = True
        self.__connection = con

        if not isinstance(con, Connection):
            raise TypeError
        con._check_thread()
        con._check_closed()
        con._cursors.append(weakref.ref(self))

        self.arraysize = 1
        self.row_factory = None
        self._reset = False
        self.__locked = False
        self.__closed = False
        self.__description = None
        self.__rowcount = -1

    def __del__(self):
        if self.__connection:
            try:
                self.__connection._cursors.remove(weakref.ref(self))
            except ValueError:
                pass
        if self.__statement:
            self.__statement._reset()

    def close(self):
        self.__connection._check_thread()
        self.__connection._check_closed()
        if self.__statement:
            self.__statement._reset()
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

    @__check_cursor_wrap
    def execute(self, sql, params=None):
        self.__locked = True
        try:
            self.__description = None
            self._reset = False
            self.__statement = self.__connection._statement_cache.get(
                sql, self.row_factory)

            if self.__connection._isolation_level is not None:
                if self.__statement._kind == Statement._DDL:
                    if self.__connection._in_transaction:
                        self.__connection.commit()
                elif self.__statement._kind == Statement._DML:
                    if not self.__connection._in_transaction:
                        self.__connection._begin()

            self.__statement._set_params(params)

            # Actually execute the SQL statement
            ret = sqlite.sqlite3_step(self.__statement._statement)
            if ret not in (SQLITE_DONE, SQLITE_ROW):
                self.__statement._reset()
                self.__connection._in_transaction = \
                        not sqlite.sqlite3_get_autocommit(self.__connection._db)
                raise self.__connection._get_exception(ret)

            if self.__statement._kind == Statement._DML:
                self.__statement._reset()

            if self.__statement._kind == Statement._DQL and ret == SQLITE_ROW:
                self.__statement._build_row_cast_map()
                self.__statement._readahead(self)
            else:
                self.__statement._item = None
                self.__statement._exhausted = True

            self.__rowcount = -1
            if self.__statement._kind == Statement._DML:
                self.__rowcount = sqlite.sqlite3_changes(self.__connection._db)
        finally:
            self.__locked = False

        return self

    @__check_cursor_wrap
    def executemany(self, sql, many_params):
        self.__locked = True
        try:
            self.__description = None
            self._reset = False
            self.__statement = self.__connection._statement_cache.get(
                sql, self.row_factory)

            if self.__statement._kind == Statement._DML:
                if self.__connection._isolation_level is not None:
                    if not self.__connection._in_transaction:
                        self.__connection._begin()
            else:
                raise ProgrammingError("executemany is only for DML statements")

            self.__rowcount = 0
            for params in many_params:
                self.__statement._set_params(params)
                ret = sqlite.sqlite3_step(self.__statement._statement)
                if ret != SQLITE_DONE:
                    self.__statement._reset()
                    self.__connection._in_transaction = \
                            not sqlite.sqlite3_get_autocommit(self.__connection._db)
                    raise self.__connection._get_exception(ret)
                self.__rowcount += sqlite.sqlite3_changes(self.__connection._db)
            self.__statement._reset()
        finally:
            self.__locked = False

        return self

    def executescript(self, sql):
        self.__description = None
        self._reset = False
        if type(sql) is unicode:
            sql = sql.encode("utf-8")
        self.__check_cursor()
        statement = c_void_p()
        c_sql = c_char_p(sql)

        self.__connection.commit()
        while True:
            rc = sqlite.sqlite3_prepare(self.__connection._db, c_sql, -1, byref(statement), byref(c_sql))
            if rc != SQLITE_OK:
                raise self.__connection._get_exception(rc)

            rc = SQLITE_ROW
            while rc == SQLITE_ROW:
                if not statement:
                    rc = SQLITE_OK
                else:
                    rc = sqlite.sqlite3_step(statement)

            if rc != SQLITE_DONE:
                sqlite.sqlite3_finalize(statement)
                if rc == SQLITE_OK:
                    return self
                else:
                    raise self.__connection._get_exception(rc)
            rc = sqlite.sqlite3_finalize(statement)
            if rc != SQLITE_OK:
                raise self.__connection._get_exception(rc)

            if not c_sql.value:
                break
        return self

    def __check_reset(self):
        if self._reset:
            raise self.__connection.InterfaceError(
                    "Cursor needed to be reset because of commit/rollback "
                    "and can no longer be fetched from.")

    # do all statements
    def fetchone(self):
        self.__check_cursor()
        self.__check_reset()

        if self.__statement is None:
            return None

        try:
            return self.__statement._next(self)
        except StopIteration:
            return None

    def fetchmany(self, size=None):
        self.__check_cursor()
        self.__check_reset()
        if self.__statement is None:
            return []
        if size is None:
            size = self.arraysize
        lst = []
        for row in self:
            lst.append(row)
            if len(lst) == size:
                break
        return lst

    def fetchall(self):
        self.__check_cursor()
        self.__check_reset()
        if self.__statement is None:
            return []
        return list(self)

    def __iter__(self):
        return iter(self.fetchone, None)

    def __get_connection(self):
        return self.__connection
    connection = property(__get_connection)

    def __get_rowcount(self):
        return self.__rowcount
    rowcount = property(__get_rowcount)

    def __get_description(self):
        if self.__description is None:
            self.__description = self.__statement._get_description()
        return self.__description
    description = property(__get_description)

    def __get_lastrowid(self):
        return sqlite.sqlite3_last_insert_rowid(self.__connection._db)
    lastrowid = property(__get_lastrowid)

    def setinputsizes(self, *args):
        pass

    def setoutputsize(self, *args):
        pass


class Statement(object):
    _DML, _DQL, _DDL = range(3)

    _statement = None

    def __init__(self, connection, sql):
        self.__con = connection

        if isinstance(sql, unicode):
            sql = sql.encode('utf-8')
        elif not isinstance(sql, str):
            raise ValueError("sql must be a string")
        first_word = self._statement_kind = sql.lstrip().split(" ")[0].upper()
        if first_word in ("INSERT", "UPDATE", "DELETE", "REPLACE"):
            self._kind = Statement._DML
        elif first_word in ("SELECT", "PRAGMA"):
            self._kind = Statement._DQL
        else:
            self._kind = Statement._DDL

        self._in_use = False
        self._exhausted = False
        self._row_factory = None

        self._statement = c_void_p()
        next_char = c_char_p()
        sql_char = c_char_p(sql)
        ret = sqlite.sqlite3_prepare_v2(self.__con._db, sql_char, -1, byref(self._statement), byref(next_char))
        if ret == SQLITE_OK and self._statement.value is None:
            # an empty statement, we work around that, as it's the least trouble
            ret = sqlite.sqlite3_prepare_v2(self.__con._db, "select 42", -1, byref(self._statement), byref(next_char))
            self._kind = Statement._DQL

        if ret != SQLITE_OK:
            raise self.__con._get_exception(ret)
        self.__con._remember_statement(self)
        if _check_remaining_sql(next_char.value):
            raise Warning("One and only one statement required: %r" %
                          (next_char.value,))

    def __del__(self):
        if self._statement:
            sqlite.sqlite3_finalize(self._statement)

    def _finalize(self):
        sqlite.sqlite3_finalize(self._statement)
        self._statement = None
        self._in_use = False

    def _reset(self):
        ret = sqlite.sqlite3_reset(self._statement)
        self._in_use = False
        self._exhausted = False
        return ret

    def _build_row_cast_map(self):
        self.__row_cast_map = []
        for i in xrange(sqlite.sqlite3_column_count(self._statement)):
            converter = None

            if self.__con._detect_types & PARSE_COLNAMES:
                colname = sqlite.sqlite3_column_name(self._statement, i)
                if colname is not None:
                    type_start = -1
                    key = None
                    for pos in range(len(colname)):
                        if colname[pos] == '[':
                            type_start = pos + 1
                        elif colname[pos] == ']' and type_start != -1:
                            key = colname[type_start:pos]
                            converter = converters[key.upper()]

            if converter is None and self.__con._detect_types & PARSE_DECLTYPES:
                decltype = sqlite.sqlite3_column_decltype(self._statement, i)
                if decltype is not None:
                    decltype = decltype.split()[0]      # if multiple words, use first, eg. "INTEGER NOT NULL" => "INTEGER"
                    if '(' in decltype:
                        decltype = decltype[:decltype.index('(')]
                    converter = converters.get(decltype.upper(), None)

            self.__row_cast_map.append(converter)

    def __check_decodable(self, param):
        if self.__con.text_factory in (unicode, OptimizedUnicode, unicode_text_factory):
            for c in param:
                if ord(c) & 0x80 != 0:
                    raise self.__con.ProgrammingError(
                        "You must not use 8-bit bytestrings unless "
                        "you use a text_factory that can interpret "
                        "8-bit bytestrings (like text_factory = str). "
                        "It is highly recommended that you instead "
                        "just switch your application to Unicode strings.")

    def __set_param(self, idx, param):
        cvt = converters.get(type(param))
        if cvt is not None:
            cvt = param = cvt(param)

        param = adapt(param)

        if param is None:
            sqlite.sqlite3_bind_null(self._statement, idx)
        elif type(param) in (bool, int, long):
            if -2147483648 <= param <= 2147483647:
                sqlite.sqlite3_bind_int(self._statement, idx, param)
            else:
                sqlite.sqlite3_bind_int64(self._statement, idx, param)
        elif type(param) is float:
            sqlite.sqlite3_bind_double(self._statement, idx, param)
        elif isinstance(param, str):
            self.__check_decodable(param)
            sqlite.sqlite3_bind_text(self._statement, idx, param, len(param), SQLITE_TRANSIENT)
        elif isinstance(param, unicode):
            param = param.encode("utf-8")
            sqlite.sqlite3_bind_text(self._statement, idx, param, len(param), SQLITE_TRANSIENT)
        elif type(param) is buffer:
            sqlite.sqlite3_bind_blob(self._statement, idx, str(param), len(param), SQLITE_TRANSIENT)
        else:
            raise InterfaceError("parameter type %s is not supported" %
                                 str(type(param)))

    def _set_params(self, params):
        ret = sqlite.sqlite3_reset(self._statement)
        if ret != SQLITE_OK:
            raise self.__con._get_exception(ret)
        self._in_use = True

        if params is None:
            if sqlite.sqlite3_bind_parameter_count(self._statement) != 0:
                raise ProgrammingError("wrong number of arguments")
            return

        params_type = None
        if isinstance(params, dict):
            params_type = dict
        else:
            params_type = list

        if params_type == list:
            if len(params) != sqlite.sqlite3_bind_parameter_count(self._statement):
                raise ProgrammingError("wrong number of arguments")

            for i in range(len(params)):
                self.__set_param(i+1, params[i])
        else:
            for idx in range(1, sqlite.sqlite3_bind_parameter_count(self._statement) + 1):
                param_name = sqlite.sqlite3_bind_parameter_name(self._statement, idx)
                if param_name is None:
                    raise ProgrammingError("need named parameters")
                param_name = param_name[1:]
                try:
                    param = params[param_name]
                except KeyError:
                    raise ProgrammingError("missing parameter '%s'" % param)
                self.__set_param(idx, param)

    def _next(self, cursor):
        self.__con._check_closed()
        self.__con._check_thread()
        if self._exhausted:
            raise StopIteration
        item = self._item

        ret = sqlite.sqlite3_step(self._statement)
        if ret == SQLITE_DONE:
            self._exhausted = True
            self._item = None
        elif ret != SQLITE_ROW:
            exc = self.__con._get_exception(ret)
            sqlite.sqlite3_reset(self._statement)
            raise exc

        self._readahead(cursor)
        return item

    def _readahead(self, cursor):
        self.column_count = sqlite.sqlite3_column_count(self._statement)
        row = []
        for i in xrange(self.column_count):
            typ = sqlite.sqlite3_column_type(self._statement, i)

            converter = self.__row_cast_map[i]
            if converter is None:
                if typ == SQLITE_INTEGER:
                    val = sqlite.sqlite3_column_int64(self._statement, i)
                    if -sys.maxint-1 <= val <= sys.maxint:
                        val = int(val)
                elif typ == SQLITE_FLOAT:
                    val = sqlite.sqlite3_column_double(self._statement, i)
                elif typ == SQLITE_BLOB:
                    blob_len = sqlite.sqlite3_column_bytes(self._statement, i)
                    blob = sqlite.sqlite3_column_blob(self._statement, i)
                    val = buffer(string_at(blob, blob_len))
                elif typ == SQLITE_NULL:
                    val = None
                elif typ == SQLITE_TEXT:
                    text_len = sqlite.sqlite3_column_bytes(self._statement, i)
                    text = sqlite.sqlite3_column_text(self._statement, i)
                    val = string_at(text, text_len)
                    val = self.__con.text_factory(val)
            else:
                blob = sqlite.sqlite3_column_blob(self._statement, i)
                if not blob:
                    val = None
                else:
                    blob_len = sqlite.sqlite3_column_bytes(self._statement, i)
                    val = string_at(blob, blob_len)
                    val = converter(val)
            row.append(val)

        row = tuple(row)
        if self._row_factory is not None:
            row = self._row_factory(cursor, row)
        self._item = row

    def _get_description(self):
        if self._kind == Statement._DML:
            return None
        desc = []
        for i in xrange(sqlite.sqlite3_column_count(self._statement)):
            name = sqlite.sqlite3_column_name(self._statement, i).split("[")[0].strip()
            desc.append((name, None, None, None, None, None, None))
        return desc


class Row(object):
    def __init__(self, cursor, values):
        self.description = cursor.description
        self.values = values

    def __getitem__(self, item):
        if type(item) is int:
            return self.values[item]
        else:
            item = item.lower()
            for idx, desc in enumerate(self.description):
                if desc[0].lower() == item:
                    return self.values[idx]
            raise KeyError

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


def _check_remaining_sql(s):
    state = "NORMAL"
    for char in s:
        if char == chr(0):
            return 0
        elif char == '-':
            if state == "NORMAL":
                state = "LINECOMMENT_1"
            elif state == "LINECOMMENT_1":
                state = "IN_LINECOMMENT"
        elif char in (' ', '\t'):
            pass
        elif char == '\n':
            if state == "IN_LINECOMMENT":
                state = "NORMAL"
        elif char == '/':
            if state == "NORMAL":
                state = "COMMENTSTART_1"
            elif state == "COMMENTEND_1":
                state = "NORMAL"
            elif state == "COMMENTSTART_1":
                return 1
        elif char == '*':
            if state == "NORMAL":
                return 1
            elif state == "LINECOMMENT_1":
                return 1
            elif state == "COMMENTSTART_1":
                state = "IN_COMMENT"
            elif state == "IN_COMMENT":
                state = "COMMENTEND_1"
        else:
            if state == "COMMENTEND_1":
                state = "IN_COMMENT"
            elif state == "IN_LINECOMMENT":
                pass
            elif state == "IN_COMMENT":
                pass
            else:
                return 1
    return 0


def _convert_params(con, nargs, params):
    _params = []
    for i in range(nargs):
        typ = sqlite.sqlite3_value_type(params[i])
        if typ == SQLITE_INTEGER:
            val = sqlite.sqlite3_value_int64(params[i])
            if -sys.maxint-1 <= val <= sys.maxint:
                val = int(val)
        elif typ == SQLITE_FLOAT:
            val = sqlite.sqlite3_value_double(params[i])
        elif typ == SQLITE_BLOB:
            blob_len = sqlite.sqlite3_value_bytes(params[i])
            blob = sqlite.sqlite3_value_blob(params[i])
            val = buffer(string_at(blob, blob_len))
        elif typ == SQLITE_NULL:
            val = None
        elif typ == SQLITE_TEXT:
            val = sqlite.sqlite3_value_text(params[i])
            # XXX changed from con.text_factory
            val = unicode(val, 'utf-8')
        else:
            raise NotImplementedError
        _params.append(val)
    return _params


def _convert_result(con, val):
    if val is None:
        sqlite.sqlite3_result_null(con)
    elif isinstance(val, (bool, int, long)):
        sqlite.sqlite3_result_int64(con, int(val))
    elif isinstance(val, str):
        # XXX ignoring unicode issue
        sqlite.sqlite3_result_text(con, val, len(val), SQLITE_TRANSIENT)
    elif isinstance(val, unicode):
        val = val.encode('utf-8')
        sqlite.sqlite3_result_text(con, val, len(val), SQLITE_TRANSIENT)
    elif isinstance(val, float):
        sqlite.sqlite3_result_double(con, val)
    elif isinstance(val, buffer):
        sqlite.sqlite3_result_blob(con, str(val), len(val), SQLITE_TRANSIENT)
    else:
        raise NotImplementedError


def function_callback(real_cb, context, nargs, c_params):
    params = _convert_params(context, nargs, c_params)
    try:
        val = real_cb(*params)
    except Exception:
        msg = "user-defined function raised exception"
        sqlite.sqlite3_result_error(context, msg, len(msg))
    else:
        _convert_result(context, val)

_FUNC = CFUNCTYPE(None, c_void_p, c_int, POINTER(c_void_p))
_STEP = CFUNCTYPE(None, c_void_p, c_int, POINTER(c_void_p))
_FINAL = CFUNCTYPE(None, c_void_p)
sqlite.sqlite3_create_function.argtypes = [c_void_p, c_char_p, c_int, c_int, c_void_p, _FUNC, _STEP, _FINAL]
sqlite.sqlite3_create_function.restype = c_int

sqlite.sqlite3_aggregate_context.argtypes = [c_void_p, c_int]
sqlite.sqlite3_aggregate_context.restype = c_void_p

_COLLATION = CFUNCTYPE(c_int, c_void_p, c_int, c_void_p, c_int, c_void_p)
sqlite.sqlite3_create_collation.argtypes = [c_void_p, c_char_p, c_int, c_void_p, _COLLATION]
sqlite.sqlite3_create_collation.restype = c_int

_PROGRESS = CFUNCTYPE(c_int, c_void_p)
sqlite.sqlite3_progress_handler.argtypes = [c_void_p, c_int, _PROGRESS, c_void_p]
sqlite.sqlite3_progress_handler.restype = c_int

_AUTHORIZER = CFUNCTYPE(c_int, c_void_p, c_int, c_char_p, c_char_p, c_char_p, c_char_p)
sqlite.sqlite3_set_authorizer.argtypes = [c_void_p, _AUTHORIZER, c_void_p]
sqlite.sqlite3_set_authorizer.restype = c_int

converters = {}
adapters = {}


class PrepareProtocol(object):
    pass


def register_adapter(typ, callable):
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
        return datetime.datetime(year, month, day,
                                 hours, minutes, seconds, microseconds)

    register_adapter(datetime.date, adapt_date)
    register_adapter(datetime.datetime, adapt_datetime)
    register_converter("date", convert_date)
    register_converter("timestamp", convert_timestamp)


def adapt(val, proto=PrepareProtocol):
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

    return val

register_adapters_and_converters()


def OptimizedUnicode(s):
    try:
        val = unicode(s, "ascii").encode("ascii")
    except UnicodeDecodeError:
        val = unicode(s, "utf-8")
    return val
