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

from ctypes import c_void_p, c_int, c_double, c_int64, c_char_p, cdll
from ctypes import POINTER, byref, string_at, CFUNCTYPE, cast
from ctypes import sizeof, c_ssize_t
import datetime
import sys
import time
import weakref
from threading import _get_ident as thread_get_ident

names = "sqlite3.dll libsqlite3.so.0 libsqlite3.so libsqlite3.dylib".split()
for name in names:
    try:
        sqlite = cdll.LoadLibrary(name)
        break
    except OSError:
        continue
else:
    raise ImportError("Could not load C-library, tried: %s" %(names,))

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

sqlite.sqlite3_bind_blob.argtypes = [c_void_p, c_int, c_void_p, c_int,c_void_p]
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
sqlite.sqlite3_bind_text.argtypes = [c_void_p, c_int, c_char_p, c_int,c_void_p]
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
sqlite.sqlite3_column_text.restype = c_char_p
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

class Connection(object):
    def __init__(self, database, timeout=5.0, detect_types=0, isolation_level="",
                 check_same_thread=True, factory=None, cached_statements=100):
        self.db = c_void_p()
        if sqlite.sqlite3_open(database, byref(self.db)) != SQLITE_OK:
            raise OperationalError("Could not open database")
        if timeout is not None:
            timeout = int(timeout * 1000) # pysqlite2 uses timeout in seconds
            sqlite.sqlite3_busy_timeout(self.db, timeout)

        self.text_factory = unicode_text_factory
        self.closed = False
        self.statements = []
        self.statement_counter = 0
        self.row_factory = None
        self._isolation_level = isolation_level
        self.detect_types = detect_types

        self.cursors = []

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

        self.func_cache = {}
        self._aggregates = {}
        self.aggregate_instances = {}
        self._collations = {}
        if check_same_thread:
            self.thread_ident = thread_get_ident()

    def _get_exception(self, error_code = None):
        if error_code is None:
            error_code = sqlite.sqlite3_errcode(self.db)
        error_message = sqlite.sqlite3_errmsg(self.db)

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
        self.statements.append(weakref.ref(statement))
        self.statement_counter += 1

        if self.statement_counter % 100 == 0:
            self.statements = [ref for ref in self.statements if ref() is not None]

    def _check_thread(self):
        if not hasattr(self, 'thread_ident'):
            return
        if self.thread_ident != thread_get_ident():
            raise ProgrammingError(
                "SQLite objects created in a thread can only be used in that same thread."
                "The object was created in thread id %d and this is thread id %d",
                self.thread_ident, thread_get_ident())

    def _reset_cursors(self):
        for cursor_ref in self.cursors:
            cursor = cursor_ref()
            if cursor:
                cursor.reset = True

    def cursor(self, factory=None):
        self._check_thread()
        self._check_closed()
        if factory is None:
            factory = Cursor
        cur = factory(self)
        if self.row_factory is not None:
            cur.row_factory = self.row_factory
        return cur

    def executemany(self, *args):
        self._check_closed()
        cur = Cursor(self)
        if self.row_factory is not None:
            cur.row_factory = self.row_factory
        return cur.executemany(*args)

    def execute(self, *args):
        self._check_closed()
        cur = Cursor(self)
        if self.row_factory is not None:
            cur.row_factory = self.row_factory
        return cur.execute(*args)

    def executescript(self, *args):
        self._check_closed()
        cur = Cursor(self)
        if self.row_factory is not None:
            cur.row_factory = self.row_factory
        return cur.executescript(*args)

    def __call__(self, sql):
        self._check_closed()
        cur = Cursor(self)
        if not isinstance(sql, (str, unicode)):
            raise Warning("SQL is of wrong type. Must be string or unicode.")
        statement = Statement(cur, sql, self.row_factory)
        return statement

    def _get_isolation_level(self):
        return self._isolation_level
    def _set_isolation_level(self, val):
        if val is None:
            self.commit()
        if isinstance(val, unicode):
            val = str(val)
        self._isolation_level = val
    isolation_level = property(_get_isolation_level, _set_isolation_level)

    def _begin(self):
        self._check_closed()
        if self._isolation_level is None:
            return
        if sqlite.sqlite3_get_autocommit(self.db):
            try:
                sql = "BEGIN " + self._isolation_level
                statement = c_void_p()
                next_char = c_char_p()
                ret = sqlite.sqlite3_prepare_v2(self.db, sql, -1, byref(statement), next_char)
                if ret != SQLITE_OK:
                    raise self._get_exception(ret)
                ret = sqlite.sqlite3_step(statement)
                if ret != SQLITE_DONE:
                    raise self._get_exception(ret)
            finally:
                sqlite.sqlite3_finalize(statement)

    def commit(self):
        self._check_thread()
        self._check_closed()
        if sqlite.sqlite3_get_autocommit(self.db):
            return

        for statement in self.statements:
            obj = statement()
            if obj is not None:
                obj.reset()

        try:
            sql = "COMMIT"
            statement = c_void_p()
            next_char = c_char_p()
            ret = sqlite.sqlite3_prepare_v2(self.db, sql, -1, byref(statement), next_char)
            if ret != SQLITE_OK:
                raise self._get_exception(ret)
            ret = sqlite.sqlite3_step(statement)
            if ret != SQLITE_DONE:
                raise self._get_exception(ret)
        finally:
            sqlite.sqlite3_finalize(statement)

    def rollback(self):
        self._check_thread()
        self._check_closed()
        if sqlite.sqlite3_get_autocommit(self.db):
            return

        for statement in self.statements:
            obj = statement()
            if obj is not None:
                obj.reset()

        try:
            sql = "ROLLBACK"
            statement = c_void_p()
            next_char = c_char_p()
            ret = sqlite.sqlite3_prepare_v2(self.db, sql, -1, byref(statement), next_char)
            if ret != SQLITE_OK:
                raise self._get_exception(ret)
            ret = sqlite.sqlite3_step(statement)
            if ret != SQLITE_DONE:
                raise self._get_exception(ret)
        finally:
            sqlite.sqlite3_finalize(statement)
            self._reset_cursors()

    def _check_closed(self):
        if getattr(self, 'closed', True):
            raise ProgrammingError("Cannot operate on a closed database.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        if exc_type is None and exc_value is None and exc_tb is None:
            self.commit()
        else:
            self.rollback()

    def _get_total_changes(self):
        return sqlite.sqlite3_total_changes(self.db)
    total_changes = property(_get_total_changes)

    def close(self):
        self._check_thread()
        if self.closed:
            return
        for statement in self.statements:
            obj = statement()
            if obj is not None:
                obj.finalize()

        self.closed = True
        ret = sqlite.sqlite3_close(self.db)
        self._reset_cursors()
        if ret != SQLITE_OK:
            raise self._get_exception(ret)

    def create_collation(self, name, callback):
        self._check_thread()
        self._check_closed()
        name = name.upper()
        if not name.replace('_', '').isalnum():
            raise ProgrammingError("invalid character in collation name")

        if callback is None:
            del self._collations[name]
            c_collation_callback = cast(None, COLLATION)
        else:
            if not callable(callback):
                raise TypeError("parameter must be callable")

            def collation_callback(context, len1, str1, len2, str2):
                text1 = string_at(str1, len1)
                text2 = string_at(str2, len2)

                return callback(text1, text2)

            c_collation_callback = COLLATION(collation_callback)
            self._collations[name] = c_collation_callback


        ret = sqlite.sqlite3_create_collation(self.db, name,
                                              SQLITE_UTF8,
                                              None,
                                              c_collation_callback)
        if ret != SQLITE_OK:
            raise self._get_exception(ret)

    def set_progress_handler(self, callable, nsteps):
        self._check_thread()
        self._check_closed()
        if callable is None:
            c_progress_handler = cast(None, PROGRESS)
        else:
            try:
                c_progress_handler, _ = self.func_cache[callable]
            except KeyError:
                def progress_handler(userdata):
                    try:
                        ret = callable()
                        return bool(ret)
                    except Exception:
                        # abort query if error occurred
                        return 1
                c_progress_handler = PROGRESS(progress_handler)

                self.func_cache[callable] = c_progress_handler, progress_handler
        ret = sqlite.sqlite3_progress_handler(self.db, nsteps,
                                              c_progress_handler,
                                              None)
        if ret != SQLITE_OK:
            raise self._get_exception(ret)

    def set_authorizer(self, callback):
        self._check_thread()
        self._check_closed()

        try:
            c_authorizer, _ = self.func_cache[callback]
        except KeyError:
            def authorizer(userdata, action, arg1, arg2, dbname, source):
                try:
                    return int(callback(action, arg1, arg2, dbname, source))
                except Exception, e:
                    return SQLITE_DENY
            c_authorizer = AUTHORIZER(authorizer)

            self.func_cache[callback] = c_authorizer, authorizer

        ret = sqlite.sqlite3_set_authorizer(self.db,
                                            c_authorizer,
                                            None)
        if ret != SQLITE_OK:
            raise self._get_exception(ret)

    def create_function(self, name, num_args, callback):
        self._check_thread()
        self._check_closed()
        try:
            c_closure, _ = self.func_cache[callback]
        except KeyError:
            def closure(context, nargs, c_params):
                function_callback(callback, context, nargs, c_params)
            c_closure = FUNC(closure)
            self.func_cache[callback] = c_closure, closure
        ret = sqlite.sqlite3_create_function(self.db, name, num_args,
                                             SQLITE_UTF8, None,
                                             c_closure,
                                             cast(None, STEP),
                                             cast(None, FINAL))
        if ret != SQLITE_OK:
            raise self.OperationalError("Error creating function")

    def create_aggregate(self, name, num_args, cls):
        self._check_thread()
        self._check_closed()

        try:
            c_step_callback, c_final_callback, _, _ = self._aggregates[cls]
        except KeyError:
            def step_callback(context, argc, c_params):

                aggregate_ptr = cast(
                    sqlite.sqlite3_aggregate_context(
                    context, sizeof(c_ssize_t)),
                    POINTER(c_ssize_t))

                if not aggregate_ptr[0]:
                    try:
                        aggregate = cls()
                    except Exception, e:
                        msg = ("user-defined aggregate's '__init__' "
                               "method raised error")
                        sqlite.sqlite3_result_error(context, msg, len(msg))
                        return
                    aggregate_id = id(aggregate)
                    self.aggregate_instances[aggregate_id] = aggregate
                    aggregate_ptr[0] = aggregate_id
                else:
                    aggregate = self.aggregate_instances[aggregate_ptr[0]]

                params = _convert_params(context, argc, c_params)
                try:
                    aggregate.step(*params)
                except Exception, e:
                    msg = ("user-defined aggregate's 'step' "
                           "method raised error")
                    sqlite.sqlite3_result_error(context, msg, len(msg))

            def final_callback(context):

                aggregate_ptr = cast(
                    sqlite.sqlite3_aggregate_context(
                    context, sizeof(c_ssize_t)),
                    POINTER(c_ssize_t))

                if aggregate_ptr[0]:
                    aggregate = self.aggregate_instances[aggregate_ptr[0]]
                    try:
                        val = aggregate.finalize()
                    except Exception, e:
                        msg = ("user-defined aggregate's 'finalize' "
                               "method raised error")
                        sqlite.sqlite3_result_error(context, msg, len(msg))
                    else:
                        _convert_result(context, val)
                    finally:
                        del self.aggregate_instances[aggregate_ptr[0]]

            c_step_callback = STEP(step_callback)
            c_final_callback = FINAL(final_callback)

            self._aggregates[cls] = (c_step_callback, c_final_callback,
                                     step_callback, final_callback)

        ret = sqlite.sqlite3_create_function(self.db, name, num_args,
                                             SQLITE_UTF8, None,
                                             cast(None, FUNC),
                                             c_step_callback,
                                             c_final_callback)
        if ret != SQLITE_OK:
            raise self._get_exception(ret)

    def iterdump(self):
        from sqlite3.dump import _iterdump
        return _iterdump(self)

class Cursor(object):
    def __init__(self, con):
        if not isinstance(con, Connection):
            raise TypeError
        con._check_thread()
        con._check_closed()
        con.cursors.append(weakref.ref(self))
        self.connection = con
        self._description = None
        self.arraysize = 1
        self.row_factory = None
        self.rowcount = -1
        self.statement = None
        self.reset = False

    def _check_closed(self):
        if not getattr(self, 'connection', None):
            raise ProgrammingError("Cannot operate on a closed cursor.")
        self.connection._check_thread()
        self.connection._check_closed()

    def execute(self, sql, params=None):
        self._description = None
        self.reset = False
        if type(sql) is unicode:
            sql = sql.encode("utf-8")
        self._check_closed()
        self.statement = Statement(self, sql, self.row_factory)

        if self.connection._isolation_level is not None:
            if self.statement.kind == "DDL":
                self.connection.commit()
            elif self.statement.kind == "DML":
                self.connection._begin()

        self.statement.set_params(params)

        # Actually execute the SQL statement
        ret = sqlite.sqlite3_step(self.statement.statement)
        if ret not in (SQLITE_DONE, SQLITE_ROW):
            self.statement.reset()
            raise self.connection._get_exception(ret)

        if self.statement.kind == "DQL"and ret == SQLITE_ROW:
            self.statement._build_row_cast_map()
            self.statement._readahead()
        else:
            self.statement.item = None
            self.statement.exhausted = True

        if self.statement.kind in ("DML", "DDL"):
            self.statement.reset()

        self.rowcount = -1
        if self.statement.kind == "DML":
            self.rowcount = sqlite.sqlite3_changes(self.connection.db)

        return self

    def executemany(self, sql, many_params):
        self._description = None
        self.reset = False
        if type(sql) is unicode:
            sql = sql.encode("utf-8")
        self._check_closed()
        self.statement = Statement(self, sql, self.row_factory)
        if self.statement.kind == "DML":
            self.connection._begin()
        else:
            raise ProgrammingError, "executemany is only for DML statements"

        self.rowcount = 0
        for params in many_params:
            self.statement.set_params(params)
            ret = sqlite.sqlite3_step(self.statement.statement)
            if ret != SQLITE_DONE:
                raise self.connection._get_exception(ret)
            self.rowcount += sqlite.sqlite3_changes(self.connection.db)

        return self

    def executescript(self, sql):
        self._description = None
        self.reset = False
        if type(sql) is unicode:
            sql = sql.encode("utf-8")
        self._check_closed()
        statement = c_void_p()
        c_sql = c_char_p(sql)

        self.connection.commit()
        while True:
            rc = sqlite.sqlite3_prepare(self.connection.db, c_sql, -1, byref(statement), byref(c_sql))
            if rc != SQLITE_OK:
                raise self.connection._get_exception(rc)

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
                    raise self.connection._get_exception(rc)
            rc = sqlite.sqlite3_finalize(statement)
            if rc != SQLITE_OK:
                raise self.connection._get_exception(rc)

            if not c_sql.value:
                break
        return self

    def __iter__(self):
        return self.statement

    def _check_reset(self):
        if self.reset:
            raise self.connection.InterfaceError("Cursor needed to be reset because "
                                                 "of commit/rollback and can "
                                                 "no longer be fetched from.")

    # do all statements
    def fetchone(self):
        self._check_closed()
        self._check_reset()

        if self.statement is None:
            return None

        try:
            return self.statement.next()
        except StopIteration:
            return None

        return nextrow

    def fetchmany(self, size=None):
        self._check_closed()
        self._check_reset()
        if self.statement is None:
            return []
        if size is None:
            size = self.arraysize
        lst = []
        for row in self.statement:
            lst.append(row)
            if len(lst) == size:
                break
        return lst

    def fetchall(self):
        self._check_closed()
        self._check_reset()
        if self.statement is None:
            return []
        return list(self.statement)

    def _getdescription(self):
        if self._description is None:
            self._description = self.statement._get_description()
        return self._description

    def _getlastrowid(self):
        return sqlite.sqlite3_last_insert_rowid(self.connection.db)

    def close(self):
        if not self.connection:
            return
        self._check_closed()
        if self.statement:
            self.statement.reset()
            self.statement = None
        self.connection.cursors.remove(weakref.ref(self))
        self.connection = None

    def setinputsizes(self, *args):
        pass
    def setoutputsize(self, *args):
        pass


    description = property(_getdescription)
    lastrowid = property(_getlastrowid)

class Statement(object):
    def __init__(self, cur, sql, row_factory):
        self.statement = None
        if not isinstance(sql, str):
            raise ValueError, "sql must be a string"
        self.con = cur.connection
        self.cur = weakref.ref(cur)
        self.sql = sql # DEBUG ONLY
        self.row_factory = row_factory
        first_word = self._statement_kind = sql.lstrip().split(" ")[0].upper()
        if first_word in ("INSERT", "UPDATE", "DELETE", "REPLACE"):
            self.kind = "DML"
        elif first_word in ("SELECT", "PRAGMA"):
            self.kind = "DQL"
        else:
            self.kind = "DDL"
        self.exhausted = False

        self.statement = c_void_p()
        next_char = c_char_p()
        sql_char = c_char_p(sql)
        ret = sqlite.sqlite3_prepare_v2(self.con.db, sql_char, -1, byref(self.statement), byref(next_char))
        if ret == SQLITE_OK and self.statement.value is None:
            # an empty statement, we work around that, as it's the least trouble
            ret = sqlite.sqlite3_prepare_v2(self.con.db, "select 42", -1, byref(self.statement), byref(next_char))
            self.kind = "DQL"

        if ret != SQLITE_OK:
            raise self.con._get_exception(ret)
        self.con._remember_statement(self)
        if _check_remaining_sql(next_char.value):
            raise Warning, "One and only one statement required: %r" % (
                next_char.value,)
        # sql_char should remain alive until here

        self._build_row_cast_map()

    def _build_row_cast_map(self):
        self.row_cast_map = []
        for i in xrange(sqlite.sqlite3_column_count(self.statement)):
            converter = None

            if self.con.detect_types & PARSE_COLNAMES:
                colname = sqlite.sqlite3_column_name(self.statement, i)
                if colname is not None:
                    type_start = -1
                    key = None
                    for pos in range(len(colname)):
                        if colname[pos] == '[':
                            type_start = pos + 1
                        elif colname[pos] == ']' and type_start != -1:
                            key = colname[type_start:pos]
                            converter = converters[key.upper()]

            if converter is None and self.con.detect_types & PARSE_DECLTYPES:
                decltype = sqlite.sqlite3_column_decltype(self.statement, i)
                if decltype is not None:
                    decltype = decltype.split()[0]      # if multiple words, use first, eg. "INTEGER NOT NULL" => "INTEGER"
                    if '(' in decltype:
                        decltype = decltype[:decltype.index('(')]
                    converter = converters.get(decltype.upper(), None)

            self.row_cast_map.append(converter)

    def _check_decodable(self, param):
        if self.con.text_factory in (unicode, OptimizedUnicode, unicode_text_factory):
            for c in param:
                if ord(c) & 0x80 != 0:
                    raise self.con.ProgrammingError(
                            "You must not use 8-bit bytestrings unless "
                            "you use a text_factory that can interpret "
                            "8-bit bytestrings (like text_factory = str). "
                            "It is highly recommended that you instead "
                            "just switch your application to Unicode strings.")

    def set_param(self, idx, param):
        cvt = converters.get(type(param))
        if cvt is not None:
            cvt = param = cvt(param)

        param = adapt(param)

        if param is None:
            sqlite.sqlite3_bind_null(self.statement, idx)
        elif type(param) in (bool, int, long):
            if -2147483648 <= param <= 2147483647:
                sqlite.sqlite3_bind_int(self.statement, idx, param)
            else:
                sqlite.sqlite3_bind_int64(self.statement, idx, param)
        elif type(param) is float:
            sqlite.sqlite3_bind_double(self.statement, idx, param)
        elif isinstance(param, str):
            self._check_decodable(param)
            sqlite.sqlite3_bind_text(self.statement, idx, param, -1, SQLITE_TRANSIENT)
        elif isinstance(param, unicode):
            param = param.encode("utf-8")
            sqlite.sqlite3_bind_text(self.statement, idx, param, -1, SQLITE_TRANSIENT)
        elif type(param) is buffer:
            sqlite.sqlite3_bind_blob(self.statement, idx, str(param), len(param), SQLITE_TRANSIENT)
        else:
            raise InterfaceError, "parameter type %s is not supported" % str(type(param))

    def set_params(self, params):
        ret = sqlite.sqlite3_reset(self.statement)
        if ret != SQLITE_OK:
            raise self.con._get_exception(ret)

        if params is None:
            if sqlite.sqlite3_bind_parameter_count(self.statement) != 0:
                raise ProgrammingError("wrong number of arguments")
            return

        params_type = None
        if isinstance(params, dict):
            params_type = dict
        else:
            params_type = list

        if params_type == list:
            if len(params) != sqlite.sqlite3_bind_parameter_count(self.statement):
                raise ProgrammingError("wrong number of arguments")

            for i in range(len(params)):
                self.set_param(i+1, params[i])
        else:
            for idx in range(1, sqlite.sqlite3_bind_parameter_count(self.statement) + 1):
                param_name = sqlite.sqlite3_bind_parameter_name(self.statement, idx)
                if param_name is None:
                    raise ProgrammingError, "need named parameters"
                param_name = param_name[1:]
                try:
                    param = params[param_name]
                except KeyError, e:
                    raise ProgrammingError("missing parameter '%s'" %param)
                self.set_param(idx, param)

    def __iter__(self):
        return self

    def next(self):
        self.con._check_closed()
        self.con._check_thread()
        if self.exhausted:
            raise StopIteration
        item = self.item

        ret = sqlite.sqlite3_step(self.statement)
        if ret == SQLITE_DONE:
            self.exhausted = True
            self.item = None
        elif ret != SQLITE_ROW:
            exc = self.con._get_exception(ret)
            sqlite.sqlite3_reset(self.statement)
            raise exc

        self._readahead()
        return item

    def _readahead(self):
        self.column_count = sqlite.sqlite3_column_count(self.statement)
        row = []
        for i in xrange(self.column_count):
            typ = sqlite.sqlite3_column_type(self.statement, i)

            converter = self.row_cast_map[i]
            if converter is None:
                if typ == SQLITE_INTEGER:
                    val = sqlite.sqlite3_column_int64(self.statement, i)
                    if -sys.maxint-1 <= val <= sys.maxint:
                        val = int(val)
                elif typ == SQLITE_FLOAT:
                    val = sqlite.sqlite3_column_double(self.statement, i)
                elif typ == SQLITE_BLOB:
                    blob_len = sqlite.sqlite3_column_bytes(self.statement, i)
                    blob = sqlite.sqlite3_column_blob(self.statement, i)
                    val = buffer(string_at(blob, blob_len))
                elif typ == SQLITE_NULL:
                    val = None
                elif typ == SQLITE_TEXT:
                    val = sqlite.sqlite3_column_text(self.statement, i)
                    val = self.con.text_factory(val)
            else:
                blob = sqlite.sqlite3_column_blob(self.statement, i)
                if not blob:
                    val = None
                else:
                    blob_len = sqlite.sqlite3_column_bytes(self.statement, i)
                    val = string_at(blob, blob_len)
                    val = converter(val)
            row.append(val)

        row = tuple(row)
        if self.row_factory is not None:
            row = self.row_factory(self.cur(), row)
        self.item = row

    def reset(self):
        self.row_cast_map = None
        return sqlite.sqlite3_reset(self.statement)

    def finalize(self):
        sqlite.sqlite3_finalize(self.statement)
        self.statement = None

    def __del__(self):
        sqlite.sqlite3_finalize(self.statement)
        self.statement = None

    def _get_description(self):
        if self.kind == "DML":
            return None
        desc = []
        for i in xrange(sqlite.sqlite3_column_count(self.statement)):
            name = sqlite.sqlite3_column_name(self.statement, i).split("[")[0].strip()
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
    _params  = []
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
    except Exception, e:
        msg = "user-defined function raised exception"
        sqlite.sqlite3_result_error(context, msg, len(msg))
    else:
        _convert_result(context, val)

FUNC = CFUNCTYPE(None, c_void_p, c_int, POINTER(c_void_p))
STEP = CFUNCTYPE(None, c_void_p, c_int, POINTER(c_void_p))
FINAL = CFUNCTYPE(None, c_void_p)
sqlite.sqlite3_create_function.argtypes = [c_void_p, c_char_p, c_int, c_int, c_void_p, FUNC, STEP, FINAL]
sqlite.sqlite3_create_function.restype = c_int

sqlite.sqlite3_aggregate_context.argtypes = [c_void_p, c_int]
sqlite.sqlite3_aggregate_context.restype = c_void_p

COLLATION = CFUNCTYPE(c_int, c_void_p, c_int, c_void_p, c_int, c_void_p)
sqlite.sqlite3_create_collation.argtypes = [c_void_p, c_char_p, c_int, c_void_p, COLLATION]
sqlite.sqlite3_create_collation.restype = c_int

PROGRESS = CFUNCTYPE(c_int, c_void_p)
sqlite.sqlite3_progress_handler.argtypes = [c_void_p, c_int, PROGRESS, c_void_p]
sqlite.sqlite3_progress_handler.restype = c_int

AUTHORIZER = CFUNCTYPE(c_int, c_void_p, c_int, c_char_p, c_char_p, c_char_p, c_char_p)
sqlite.sqlite3_set_authorizer.argtypes = [c_void_p, AUTHORIZER, c_void_p]
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

        val = datetime.datetime(year, month, day, hours, minutes, seconds, microseconds)
        return val


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
