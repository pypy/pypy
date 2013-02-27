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

from collections import OrderedDict
import datetime
import sys
import weakref
from threading import _get_ident as thread_get_ident

from cffi import FFI

ffi = FFI()

ffi.cdef("""
#define SQLITE_OK ...
#define SQLITE_ERROR ...
#define SQLITE_INTERNAL ...
#define SQLITE_PERM ...
#define SQLITE_ABORT ...
#define SQLITE_BUSY ...
#define SQLITE_LOCKED ...
#define SQLITE_NOMEM ...
#define SQLITE_READONLY ...
#define SQLITE_INTERRUPT ...
#define SQLITE_IOERR ...
#define SQLITE_CORRUPT ...
#define SQLITE_NOTFOUND ...
#define SQLITE_FULL ...
#define SQLITE_CANTOPEN ...
#define SQLITE_PROTOCOL ...
#define SQLITE_EMPTY ...
#define SQLITE_SCHEMA ...
#define SQLITE_TOOBIG ...
#define SQLITE_CONSTRAINT ...
#define SQLITE_MISMATCH ...
#define SQLITE_MISUSE ...
#define SQLITE_NOLFS ...
#define SQLITE_AUTH ...
#define SQLITE_FORMAT ...
#define SQLITE_RANGE ...
#define SQLITE_NOTADB ...
#define SQLITE_ROW ...
#define SQLITE_DONE ...
#define SQLITE_INTEGER ...
#define SQLITE_FLOAT ...
#define SQLITE_BLOB ...
#define SQLITE_NULL ...
#define SQLITE_TEXT ...
#define SQLITE3_TEXT ...

#define SQLITE_TRANSIENT ...
#define SQLITE_UTF8 ...

#define SQLITE_DENY ...
#define SQLITE_IGNORE ...

#define SQLITE_CREATE_INDEX ...
#define SQLITE_CREATE_TABLE ...
#define SQLITE_CREATE_TEMP_INDEX ...
#define SQLITE_CREATE_TEMP_TABLE ...
#define SQLITE_CREATE_TEMP_TRIGGER ...
#define SQLITE_CREATE_TEMP_VIEW ...
#define SQLITE_CREATE_TRIGGER ...
#define SQLITE_CREATE_VIEW ...
#define SQLITE_DELETE ...
#define SQLITE_DROP_INDEX ...
#define SQLITE_DROP_TABLE ...
#define SQLITE_DROP_TEMP_INDEX ...
#define SQLITE_DROP_TEMP_TABLE ...
#define SQLITE_DROP_TEMP_TRIGGER ...
#define SQLITE_DROP_TEMP_VIEW ...
#define SQLITE_DROP_TRIGGER ...
#define SQLITE_DROP_VIEW ...
#define SQLITE_INSERT ...
#define SQLITE_PRAGMA ...
#define SQLITE_READ ...
#define SQLITE_SELECT ...
#define SQLITE_TRANSACTION ...
#define SQLITE_UPDATE ...
#define SQLITE_ATTACH ...
#define SQLITE_DETACH ...
#define SQLITE_ALTER_TABLE ...
#define SQLITE_REINDEX ...
#define SQLITE_ANALYZE ...
#define SQLITE_CREATE_VTABLE ...
#define SQLITE_DROP_VTABLE ...
#define SQLITE_FUNCTION ...

const char *sqlite3_libversion(void);

typedef ... sqlite3;
typedef ... sqlite3_stmt;
typedef ... sqlite3_context;
typedef ... sqlite3_value;
typedef int64_t sqlite3_int64;
typedef uint64_t sqlite3_uint64;

int sqlite3_open(
  const char *filename,   /* Database filename (UTF-8) */
  sqlite3 **ppDb          /* OUT: SQLite db handle */
);

int sqlite3_close(sqlite3 *);

int sqlite3_busy_timeout(sqlite3*, int ms);
int sqlite3_prepare_v2(
  sqlite3 *db,            /* Database handle */
  const char *zSql,       /* SQL statement, UTF-8 encoded */
  int nByte,              /* Maximum length of zSql in bytes. */
  sqlite3_stmt **ppStmt,  /* OUT: Statement handle */
  const char **pzTail     /* OUT: Pointer to unused portion of zSql */
);
int sqlite3_finalize(sqlite3_stmt *pStmt);
int sqlite3_column_count(sqlite3_stmt *pStmt);
const char *sqlite3_column_name(sqlite3_stmt*, int N);
int sqlite3_get_autocommit(sqlite3*);
int sqlite3_reset(sqlite3_stmt *pStmt);
int sqlite3_step(sqlite3_stmt*);
int sqlite3_errcode(sqlite3 *db);
const char *sqlite3_errmsg(sqlite3*);
int sqlite3_changes(sqlite3*);

int sqlite3_bind_blob(sqlite3_stmt*, int, const void*, int n, void(*)(void*));
int sqlite3_bind_double(sqlite3_stmt*, int, double);
int sqlite3_bind_int(sqlite3_stmt*, int, int);
int sqlite3_bind_int64(sqlite3_stmt*, int, sqlite3_int64);
int sqlite3_bind_null(sqlite3_stmt*, int);
int sqlite3_bind_text(sqlite3_stmt*, int, const char*, int n, void(*)(void*));
int sqlite3_bind_text16(sqlite3_stmt*, int, const void*, int, void(*)(void*));
int sqlite3_bind_value(sqlite3_stmt*, int, const sqlite3_value*);
int sqlite3_bind_zeroblob(sqlite3_stmt*, int, int n);

const void *sqlite3_column_blob(sqlite3_stmt*, int iCol);
int sqlite3_column_bytes(sqlite3_stmt*, int iCol);
double sqlite3_column_double(sqlite3_stmt*, int iCol);
int sqlite3_column_int(sqlite3_stmt*, int iCol);
sqlite3_int64 sqlite3_column_int64(sqlite3_stmt*, int iCol);
const unsigned char *sqlite3_column_text(sqlite3_stmt*, int iCol);
const void *sqlite3_column_text16(sqlite3_stmt*, int iCol);
int sqlite3_column_type(sqlite3_stmt*, int iCol);
const char *sqlite3_column_decltype(sqlite3_stmt*,int);

void sqlite3_progress_handler(sqlite3*, int, int(*)(void*), void*);
int sqlite3_create_collation(
  sqlite3*,
  const char *zName,
  int eTextRep,
  void*,
  int(*xCompare)(void*,int,const void*,int,const void*)
);
int sqlite3_set_authorizer(
  sqlite3*,
  int (*xAuth)(void*,int,const char*,const char*,const char*,const char*),
  void *pUserData
);
int sqlite3_create_function(
  sqlite3 *db,
  const char *zFunctionName,
  int nArg,
  int eTextRep,
  void *pApp,
  void (*xFunc)(sqlite3_context*,int,sqlite3_value**),
  void (*xStep)(sqlite3_context*,int,sqlite3_value**),
  void (*xFinal)(sqlite3_context*)
);
void *sqlite3_aggregate_context(sqlite3_context*, int nBytes);

sqlite3_int64 sqlite3_last_insert_rowid(sqlite3*);
int sqlite3_bind_parameter_count(sqlite3_stmt*);
const char *sqlite3_bind_parameter_name(sqlite3_stmt*, int);
int sqlite3_total_changes(sqlite3*);

int sqlite3_prepare(
  sqlite3 *db,            /* Database handle */
  const char *zSql,       /* SQL statement, UTF-8 encoded */
  int nByte,              /* Maximum length of zSql in bytes. */
  sqlite3_stmt **ppStmt,  /* OUT: Statement handle */
  const char **pzTail     /* OUT: Pointer to unused portion of zSql */
);

void sqlite3_result_blob(sqlite3_context*, const void*, int, void(*)(void*));
void sqlite3_result_double(sqlite3_context*, double);
void sqlite3_result_error(sqlite3_context*, const char*, int);
void sqlite3_result_error16(sqlite3_context*, const void*, int);
void sqlite3_result_error_toobig(sqlite3_context*);
void sqlite3_result_error_nomem(sqlite3_context*);
void sqlite3_result_error_code(sqlite3_context*, int);
void sqlite3_result_int(sqlite3_context*, int);
void sqlite3_result_int64(sqlite3_context*, sqlite3_int64);
void sqlite3_result_null(sqlite3_context*);
void sqlite3_result_text(sqlite3_context*, const char*, int, void(*)(void*));
void sqlite3_result_text16(sqlite3_context*, const void*, int, void(*)(void*));
void sqlite3_result_text16le(sqlite3_context*,const void*, int,void(*)(void*));
void sqlite3_result_text16be(sqlite3_context*,const void*, int,void(*)(void*));
void sqlite3_result_value(sqlite3_context*, sqlite3_value*);
void sqlite3_result_zeroblob(sqlite3_context*, int n);

const void *sqlite3_value_blob(sqlite3_value*);
int sqlite3_value_bytes(sqlite3_value*);
int sqlite3_value_bytes16(sqlite3_value*);
double sqlite3_value_double(sqlite3_value*);
int sqlite3_value_int(sqlite3_value*);
sqlite3_int64 sqlite3_value_int64(sqlite3_value*);
const unsigned char *sqlite3_value_text(sqlite3_value*);
const void *sqlite3_value_text16(sqlite3_value*);
const void *sqlite3_value_text16le(sqlite3_value*);
const void *sqlite3_value_text16be(sqlite3_value*);
int sqlite3_value_type(sqlite3_value*);
int sqlite3_value_numeric_type(sqlite3_value*);
""")

lib = ffi.verify("""
#include <sqlite3.h>
""", libraries=['sqlite3'])

exported_sqlite_symbols = [
    'SQLITE_ALTER_TABLE',
    'SQLITE_ANALYZE',
    'SQLITE_ATTACH',
    'SQLITE_CREATE_INDEX',
    'SQLITE_CREATE_TABLE',
    'SQLITE_CREATE_TEMP_INDEX',
    'SQLITE_CREATE_TEMP_TABLE',
    'SQLITE_CREATE_TEMP_TRIGGER',
    'SQLITE_CREATE_TEMP_VIEW',
    'SQLITE_CREATE_TRIGGER',
    'SQLITE_CREATE_VIEW',
    'SQLITE_DELETE',
    'SQLITE_DENY',
    'SQLITE_DETACH',
    'SQLITE_DROP_INDEX',
    'SQLITE_DROP_TABLE',
    'SQLITE_DROP_TEMP_INDEX',
    'SQLITE_DROP_TEMP_TABLE',
    'SQLITE_DROP_TEMP_TRIGGER',
    'SQLITE_DROP_TEMP_VIEW',
    'SQLITE_DROP_TRIGGER',
    'SQLITE_DROP_VIEW',
    'SQLITE_IGNORE',
    'SQLITE_INSERT',
    'SQLITE_OK',
    'SQLITE_PRAGMA',
    'SQLITE_READ',
    'SQLITE_REINDEX',
    'SQLITE_SELECT',
    'SQLITE_TRANSACTION',
    'SQLITE_UPDATE',
]

for symbol in exported_sqlite_symbols:
    globals()[symbol] = getattr(lib, symbol)


_SQLITE_TRANSIENT = ffi.cast('void *', lib.SQLITE_TRANSIENT)


# pysqlite version information
version = "2.6.0"

# pysqlite constants
PARSE_COLNAMES = 1
PARSE_DECLTYPES = 2

# SQLite version information
sqlite_version = ffi.string(lib.sqlite3_libversion())


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


class StatementCache(object):
    def __init__(self, connection, maxcount):
        self.connection = connection
        self.maxcount = maxcount
        self.cache = OrderedDict()

    def get(self, sql, row_factory):
        try:
            stat = self.cache[sql]
        except KeyError:
            stat = Statement(self.connection, sql)
            self.cache[sql] = stat
            if len(self.cache) > self.maxcount:
                self.cache.popitem(0)
        #
        if stat.in_use:
            stat = Statement(self.connection, sql)
        stat.set_row_factory(row_factory)
        return stat


class Connection(object):
    def __init__(self, database, timeout=5.0, detect_types=0,
                 isolation_level="", check_same_thread=True, factory=None,
                 cached_statements=100):
        db_star = ffi.new('sqlite3 **')
        if isinstance(database, unicode):
            database = database.encode("utf-8")
        if lib.sqlite3_open(database, db_star) != lib.SQLITE_OK:
            raise OperationalError("Could not open database")
        self.db = db_star[0]
        if timeout is not None:
            timeout = int(timeout * 1000)  # pysqlite2 uses timeout in seconds
            lib.sqlite3_busy_timeout(self.db, timeout)

        self.text_factory = unicode_text_factory
        self.closed = False
        self.statements = []
        self.statement_counter = 0
        self.row_factory = None
        self._isolation_level = isolation_level
        self.detect_types = detect_types
        self.statement_cache = StatementCache(self, cached_statements)

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

    def _get_exception(self, error_code=None):
        if error_code is None:
            error_code = lib.sqlite3_errcode(self.db)
        error_message = ffi.string(lib.sqlite3_errmsg(self.db))

        if error_code == lib.SQLITE_OK:
            raise ValueError("error signalled but got lib.SQLITE_OK")
        elif error_code in (lib.SQLITE_INTERNAL, lib.SQLITE_NOTFOUND):
            exc = InternalError
        elif error_code == lib.SQLITE_NOMEM:
            exc = MemoryError
        elif error_code in (
                lib.SQLITE_ERROR, lib.SQLITE_PERM, lib.SQLITE_ABORT,
                lib.SQLITE_BUSY, lib.SQLITE_LOCKED, lib.SQLITE_READONLY,
                lib.SQLITE_INTERRUPT, lib.SQLITE_IOERR, lib.SQLITE_FULL,
                lib.SQLITE_CANTOPEN, lib.SQLITE_PROTOCOL, lib.SQLITE_EMPTY,
                lib.SQLITE_SCHEMA):
            exc = OperationalError
        elif error_code == lib.SQLITE_CORRUPT:
            exc = DatabaseError
        elif error_code == lib.SQLITE_TOOBIG:
            exc = DataError
        elif error_code in (lib.SQLITE_CONSTRAINT, lib.SQLITE_MISMATCH):
            exc = IntegrityError
        elif error_code == lib.SQLITE_MISUSE:
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
            self.statements = [ref for ref in self.statements
                               if ref() is not None]

    def _check_thread(self):
        if not hasattr(self, 'thread_ident'):
            return
        if self.thread_ident != thread_get_ident():
            raise ProgrammingError(
                "SQLite objects created in a thread can only be used in that "
                "same thread. The object was created in thread id %d and this "
                "is thread id %d", self.thread_ident, thread_get_ident())

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
        if not isinstance(sql, (str, unicode)):
            raise Warning("SQL is of wrong type. Must be string or unicode.")
        statement = self.statement_cache.get(sql, self.row_factory)
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
        if lib.sqlite3_get_autocommit(self.db):
            sql = "BEGIN " + self._isolation_level
            statement_star = ffi.new('sqlite3_stmt **')
            next_char = ffi.new('char **')
            ret = lib.sqlite3_prepare_v2(self.db, sql, -1, statement_star,
                                         next_char)
            try:
                if ret != lib.SQLITE_OK:
                    raise self._get_exception(ret)
                ret = lib.sqlite3_step(statement_star[0])
                if ret != lib.SQLITE_DONE:
                    raise self._get_exception(ret)
            finally:
                lib.sqlite3_finalize(statement_star[0])

    def commit(self):
        self._check_thread()
        self._check_closed()
        if lib.sqlite3_get_autocommit(self.db):
            return

        for statement in self.statements:
            obj = statement()
            if obj is not None:
                obj.reset()

        sql = "COMMIT"
        statement_star = ffi.new('sqlite3_stmt **')
        next_char = ffi.new('char **')
        ret = lib.sqlite3_prepare_v2(self.db, sql, -1, statement_star,
                                     next_char)
        try:
            if ret != lib.SQLITE_OK:
                raise self._get_exception(ret)
            ret = lib.sqlite3_step(statement_star[0])
            if ret != lib.SQLITE_DONE:
                raise self._get_exception(ret)
        finally:
            lib.sqlite3_finalize(statement_star[0])

    def rollback(self):
        self._check_thread()
        self._check_closed()
        if lib.sqlite3_get_autocommit(self.db):
            return

        for statement in self.statements:
            obj = statement()
            if obj is not None:
                obj.reset()

        sql = "ROLLBACK"
        statement_star = ffi.new('sqlite3_stmt **')
        next_char = ffi.new('char **')
        ret = lib.sqlite3_prepare_v2(self.db, sql, -1, statement_star,
                                     next_char)
        try:
            if ret != lib.SQLITE_OK:
                raise self._get_exception(ret)
            ret = lib.sqlite3_step(statement_star[0])
            if ret != lib.SQLITE_DONE:
                raise self._get_exception(ret)
        finally:
            lib.sqlite3_finalize(statement_star[0])
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
        return lib.sqlite3_total_changes(self.db)
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
        ret = lib.sqlite3_close(self.db)
        self._reset_cursors()
        if ret != lib.SQLITE_OK:
            raise self._get_exception(ret)

    def create_collation(self, name, callback):
        self._check_thread()
        self._check_closed()
        name = name.upper()
        if not name.replace('_', '').isalnum():
            raise ProgrammingError("invalid character in collation name")

        if callback is None:
            del self._collations[name]
            collation_callback = ffi.NULL
        else:
            if not callable(callback):
                raise TypeError("parameter must be callable")

            @ffi.callback("int(void*, int, const void*, int, const void*)")
            def collation_callback(context, len1, str1, len2, str2):
                text1 = ffi.buffer(str1, len1)[:]
                text2 = ffi.buffer(str2, len2)[:]

                return callback(text1, text2)

            self._collations[name] = collation_callback

        ret = lib.sqlite3_create_collation(self.db, name, lib.SQLITE_UTF8,
                                           ffi.NULL, collation_callback)
        if ret != lib.SQLITE_OK:
            raise self._get_exception(ret)

    def set_progress_handler(self, callable, nsteps):
        self._check_thread()
        self._check_closed()
        if callable is None:
            progress_handler = ffi.NULL
        else:
            try:
                progress_handler = self.func_cache[callable]
            except KeyError:
                @ffi.callback("int(void*)")
                def progress_handler(userdata):
                    try:
                        ret = callable()
                        return bool(ret)
                    except Exception:
                        # abort query if error occurred
                        return 1

                self.func_cache[callable] = progress_handler
        lib.sqlite3_progress_handler(self.db, nsteps, progress_handler,
                                     ffi.NULL)

    def set_authorizer(self, callback):
        self._check_thread()
        self._check_closed()

        try:
            authorizer = self.func_cache[callback]
        except KeyError:
            @ffi.callback("int(void*, int, const char*, const char*, "
                          "const char*, const char*)")
            def authorizer(userdata, action, arg1, arg2, dbname, source):
                try:
                    return int(callback(action, arg1, arg2, dbname, source))
                except Exception:
                    return lib.SQLITE_DENY
            self.func_cache[callback] = authorizer

        ret = lib.sqlite3_set_authorizer(self.db, authorizer, ffi.NULL)
        if ret != lib.SQLITE_OK:
            raise self._get_exception(ret)

    def create_function(self, name, num_args, callback):
        self._check_thread()
        self._check_closed()
        try:
            closure = self.func_cache[callback]
        except KeyError:
            @ffi.callback("void(sqlite3_context*, int, sqlite3_value**)")
            def closure(context, nargs, c_params):
                function_callback(callback, context, nargs, c_params)
            self.func_cache[callback] = closure
        ret = lib.sqlite3_create_function(self.db, name, num_args,
                                          lib.SQLITE_UTF8, ffi.NULL,
                                          closure, ffi.NULL, ffi.NULL)
        if ret != lib.SQLITE_OK:
            raise self.OperationalError("Error creating function")

    def create_aggregate(self, name, num_args, cls):
        self._check_thread()
        self._check_closed()

        try:
            step_callback, final_callback = self._aggregates[cls]
        except KeyError:
            @ffi.callback("void(sqlite3_context*, int, sqlite3_value**)")
            def step_callback(context, argc, c_params):
                res = lib.sqlite3_aggregate_context(context,
                                                    ffi.sizeof("size_t"))
                aggregate_ptr = ffi.cast("size_t *", res)

                if not aggregate_ptr[0]:
                    try:
                        aggregate = cls()
                    except Exception:
                        msg = ("user-defined aggregate's '__init__' "
                               "method raised error")
                        lib.sqlite3_result_error(context, msg, len(msg))
                        return
                    aggregate_id = id(aggregate)
                    self.aggregate_instances[aggregate_id] = aggregate
                    aggregate_ptr[0] = aggregate_id
                else:
                    aggregate = self.aggregate_instances[aggregate_ptr[0]]

                params = _convert_params(context, argc, c_params)
                try:
                    aggregate.step(*params)
                except Exception:
                    msg = ("user-defined aggregate's 'step' "
                           "method raised error")
                    lib.sqlite3_result_error(context, msg, len(msg))

            @ffi.callback("void(sqlite3_context*)")
            def final_callback(context):
                res = lib.sqlite3_aggregate_context(context,
                                                    ffi.sizeof("size_t"))
                aggregate_ptr = ffi.cast("size_t", res)

                if aggregate_ptr[0]:
                    aggregate = self.aggregate_instances[aggregate_ptr[0]]
                    try:
                        val = aggregate.finalize()
                    except Exception:
                        msg = ("user-defined aggregate's 'finalize' "
                               "method raised error")
                        lib.sqlite3_result_error(context, msg, len(msg))
                    else:
                        _convert_result(context, val)
                    finally:
                        del self.aggregate_instances[aggregate_ptr[0]]

            self._aggregates[cls] = step_callback, final_callback

        ret = lib.sqlite3_create_function(self.db, name, num_args,
                                          lib.SQLITE_UTF8, ffi.NULL, ffi.NULL,
                                          step_callback, final_callback)
        if ret != lib.SQLITE_OK:
            raise self._get_exception(ret)

    def iterdump(self):
        from sqlite3.dump import _iterdump
        return _iterdump(self)

    if False and lib.HAS_LOAD_EXTENSION:
        def enable_load_extension(self, enabled):
            self._check_thread()
            self._check_closed()

            rc = lib.sqlite3_enable_load_extension(self.db, int(enabled))
            if rc != lib.SQLITE_OK:
                raise OperationalError("Error enabling load extension")


DML, DQL, DDL = range(3)


class CursorLock(object):
    def __init__(self, cursor):
        self.cursor = cursor

    def __enter__(self):
        if self.cursor.locked:
            raise ProgrammingError("Recursive use of cursors not allowed.")
        self.cursor.locked = True

    def __exit__(self, *args):
        self.cursor.locked = False


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
        self.locked = False

    def _check_closed(self):
        if not getattr(self, 'connection', None):
            raise ProgrammingError("Cannot operate on a closed cursor.")
        self.connection._check_thread()
        self.connection._check_closed()

    def _check_and_lock(self):
        self._check_closed()
        return CursorLock(self)

    def execute(self, sql, params=None):
        if type(sql) is unicode:
            sql = sql.encode("utf-8")

        with self._check_and_lock():
            self._description = None
            self.reset = False
            self.statement = self.connection.statement_cache.get(
                sql, self.row_factory)

            if self.connection._isolation_level is not None:
                if self.statement.kind == DDL:
                    self.connection.commit()
                elif self.statement.kind == DML:
                    self.connection._begin()

            self.statement.set_params(params)

            # Actually execute the SQL statement
            ret = lib.sqlite3_step(self.statement.statement)
            if ret not in (lib.SQLITE_DONE, lib.SQLITE_ROW):
                self.statement.reset()
                raise self.connection._get_exception(ret)

            if self.statement.kind == DML:
                self.statement.reset()

            if self.statement.kind == DQL and ret == lib.SQLITE_ROW:
                self.statement._build_row_cast_map()
                self.statement._readahead(self)
            else:
                self.statement.item = None
                self.statement.exhausted = True

            self.rowcount = -1
            if self.statement.kind == DML:
                self.rowcount = lib.sqlite3_changes(self.connection.db)

        return self

    def executemany(self, sql, many_params):
        if type(sql) is unicode:
            sql = sql.encode("utf-8")

        with self._check_and_lock():
            self._description = None
            self.reset = False
            self.statement = self.connection.statement_cache.get(
                sql, self.row_factory)

            if self.statement.kind == DML:
                self.connection._begin()
            else:
                raise ProgrammingError(
                    "executemany is only for DML statements")

            self.rowcount = 0
            for params in many_params:
                self.statement.set_params(params)
                ret = lib.sqlite3_step(self.statement.statement)
                if ret != lib.SQLITE_DONE:
                    raise self.connection._get_exception(ret)
                self.rowcount += lib.sqlite3_changes(self.connection.db)

        return self

    def executescript(self, sql):
        self._description = None
        self.reset = False
        if type(sql) is unicode:
            sql = sql.encode("utf-8")
        self._check_closed()
        statement_star = ffi.new('sqlite3_stmt **')
        tail = ffi.new('char **')

        self.connection.commit()
        while True:
            rc = lib.sqlite3_prepare(self.connection.db, sql, -1,
                                     statement_star, tail)
            sql = ffi.string(tail[0])
            if rc != lib.SQLITE_OK:
                raise self.connection._get_exception(rc)

            rc = lib.SQLITE_ROW
            while rc == lib.SQLITE_ROW:
                if not statement_star[0]:
                    rc = lib.SQLITE_OK
                else:
                    rc = lib.sqlite3_step(statement_star[0])

            if rc != lib.SQLITE_DONE:
                lib.sqlite3_finalize(statement_star[0])
                if rc == lib.SQLITE_OK:
                    return self
                else:
                    raise self.connection._get_exception(rc)
            rc = lib.sqlite3_finalize(statement_star[0])
            if rc != lib.SQLITE_OK:
                raise self.connection._get_exception(rc)

            if not sql:
                break
        return self

    def __iter__(self):
        return iter(self.fetchone, None)

    def _check_reset(self):
        if self.reset:
            raise self.connection.InterfaceError(
                "Cursor needed to be reset because of commit/rollback and can "
                "no longer be fetched from.")

    # do all statements
    def fetchone(self):
        self._check_closed()
        self._check_reset()

        if self.statement is None:
            return None

        try:
            return self.statement.next(self)
        except StopIteration:
            return None

    def fetchmany(self, size=None):
        self._check_closed()
        self._check_reset()
        if self.statement is None:
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
        self._check_closed()
        self._check_reset()
        if self.statement is None:
            return []
        return list(self)

    def _getdescription(self):
        if self._description is None:
            self._description = self.statement._get_description()
        return self._description

    def _getlastrowid(self):
        return lib.sqlite3_last_insert_rowid(self.connection.db)

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
    def __init__(self, connection, sql):
        self.statement = None
        if not isinstance(sql, str):
            raise ValueError("sql must be a string")
        self.con = connection
        self.sql = sql  # DEBUG ONLY
        first_word = self._statement_kind = sql.lstrip().split(" ")[0].upper()
        if first_word in ("INSERT", "UPDATE", "DELETE", "REPLACE"):
            self.kind = DML
        elif first_word in ("SELECT", "PRAGMA"):
            self.kind = DQL
        else:
            self.kind = DDL
        self.exhausted = False
        self.in_use = False
        #
        # set by set_row_factory
        self.row_factory = None

        statement_star = ffi.new('sqlite3_stmt **')
        next_char = ffi.new('char **')
        ret = lib.sqlite3_prepare_v2(self.con.db, sql, -1,
                                     statement_star, next_char)
        self.statement = statement_star[0]
        if ret == lib.SQLITE_OK and not self.statement:
            # an empty statement, we work around that as it's the least trouble
            ret = lib.sqlite3_prepare_v2(self.con.db, "select 42", -1,
                                         statement_star, next_char)
            self.statement = statement_star[0]
            self.kind = DQL

        if ret != lib.SQLITE_OK:
            raise self.con._get_exception(ret)
        self.con._remember_statement(self)
        if _check_remaining_sql(ffi.string(next_char[0])):
            raise Warning("One and only one statement required: %r" % (
                next_char[0],))
        # sql_char should remain alive until here

        self._build_row_cast_map()

    def set_row_factory(self, row_factory):
        self.row_factory = row_factory

    def _build_row_cast_map(self):
        self.row_cast_map = []
        for i in xrange(lib.sqlite3_column_count(self.statement)):
            converter = None

            if self.con.detect_types & PARSE_COLNAMES:
                colname = lib.sqlite3_column_name(self.statement, i)
                if colname != ffi.NULL:
                    colname = ffi.string(colname)
                    type_start = -1
                    key = None
                    for pos in range(len(colname)):
                        if colname[pos] == '[':
                            type_start = pos + 1
                        elif colname[pos] == ']' and type_start != -1:
                            key = colname[type_start:pos]
                            converter = converters[key.upper()]

            if converter is None and self.con.detect_types & PARSE_DECLTYPES:
                decltype = lib.sqlite3_column_decltype(self.statement, i)
                if decltype is not ffi.NULL:
                    # if multiple words, use first,
                    # eg. "INTEGER NOT NULL" => "INTEGER"
                    decltype = ffi.string(decltype).split()[0]
                    if '(' in decltype:
                        decltype = decltype[:decltype.index('(')]
                    converter = converters.get(decltype.upper(), None)

            self.row_cast_map.append(converter)

    def _check_decodable(self, param):
        if self.con.text_factory in (unicode, OptimizedUnicode,
                                     unicode_text_factory):
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
            lib.sqlite3_bind_null(self.statement, idx)
        elif type(param) in (bool, int, long):
            if -2147483648 <= param <= 2147483647:
                lib.sqlite3_bind_int(self.statement, idx, param)
            else:
                lib.sqlite3_bind_int64(self.statement, idx, param)
        elif type(param) is float:
            lib.sqlite3_bind_double(self.statement, idx, param)
        elif isinstance(param, str):
            self._check_decodable(param)
            lib.sqlite3_bind_text(self.statement, idx, param, len(param),
                                  _SQLITE_TRANSIENT)
        elif isinstance(param, unicode):
            param = param.encode("utf-8")
            lib.sqlite3_bind_text(self.statement, idx, param, len(param),
                                  _SQLITE_TRANSIENT)
        elif type(param) is buffer:
            lib.sqlite3_bind_blob(self.statement, idx, str(param), len(param),
                                  _SQLITE_TRANSIENT)
        else:
            raise InterfaceError(
                "parameter type %s is not supported" % str(type(param)))

    def set_params(self, params):
        ret = lib.sqlite3_reset(self.statement)
        if ret != lib.SQLITE_OK:
            raise self.con._get_exception(ret)
        self.mark_dirty()

        if params is None:
            if lib.sqlite3_bind_parameter_count(self.statement) != 0:
                raise ProgrammingError("wrong number of arguments")
            return

        params_type = None
        if isinstance(params, dict):
            params_type = dict
        else:
            params_type = list

        if params_type == list:
            if len(params) != lib.sqlite3_bind_parameter_count(self.statement):
                raise ProgrammingError("wrong number of arguments")

            for i in range(len(params)):
                self.set_param(i + 1, params[i])
        else:
            param_count = lib.sqlite3_bind_parameter_count(self.statement)
            for idx in range(1, param_count + 1):
                param_name = lib.sqlite3_bind_parameter_name(self.statement,
                                                             idx)
                if param_name == ffi.NULL:
                    raise ProgrammingError("need named parameters")
                param_name = ffi.string(param_name)[1:]
                try:
                    param = params[param_name]
                except KeyError:
                    raise ProgrammingError("missing parameter '%s'" % param)
                self.set_param(idx, param)

    def next(self, cursor):
        self.con._check_closed()
        self.con._check_thread()
        if self.exhausted:
            raise StopIteration
        item = self.item

        ret = lib.sqlite3_step(self.statement)
        if ret == lib.SQLITE_DONE:
            self.exhausted = True
            self.item = None
        elif ret != lib.SQLITE_ROW:
            exc = self.con._get_exception(ret)
            lib.sqlite3_reset(self.statement)
            raise exc

        self._readahead(cursor)
        return item

    def _readahead(self, cursor):
        self.column_count = lib.sqlite3_column_count(self.statement)
        row = []
        for i in xrange(self.column_count):
            typ = lib.sqlite3_column_type(self.statement, i)

            converter = self.row_cast_map[i]
            if converter is None:
                if typ == lib.SQLITE_INTEGER:
                    val = lib.sqlite3_column_int64(self.statement, i)
                    if -sys.maxint - 1 <= val <= sys.maxint:
                        val = int(val)
                elif typ == lib.SQLITE_FLOAT:
                    val = lib.sqlite3_column_double(self.statement, i)
                elif typ == lib.SQLITE_BLOB:
                    blob_len = lib.sqlite3_column_bytes(self.statement, i)
                    blob = lib.sqlite3_column_blob(self.statement, i)
                    val = buffer(ffi.buffer(blob, blob_len))
                elif typ == lib.SQLITE_NULL:
                    val = None
                elif typ == lib.SQLITE_TEXT:
                    text_len = lib.sqlite3_column_bytes(self.statement, i)
                    text = lib.sqlite3_column_text(self.statement, i)
                    val = ffi.buffer(text, text_len)[:]
                    val = self.con.text_factory(val)
            else:
                blob = lib.sqlite3_column_blob(self.statement, i)
                if not blob:
                    val = None
                else:
                    blob_len = lib.sqlite3_column_bytes(self.statement, i)
                    val = ffi.buffer(blob, blob_len)[:]
                    val = converter(val)
            row.append(val)

        row = tuple(row)
        if self.row_factory is not None:
            row = self.row_factory(cursor, row)
        self.item = row

    def reset(self):
        self.row_cast_map = None
        ret = lib.sqlite3_reset(self.statement)
        self.in_use = False
        self.exhausted = False
        return ret

    def finalize(self):
        lib.sqlite3_finalize(self.statement)
        self.statement = None
        self.in_use = False

    def mark_dirty(self):
        self.in_use = True

    def __del__(self):
        lib.sqlite3_finalize(self.statement)
        self.statement = None

    def _get_description(self):
        if self.kind == DML:
            return None
        desc = []
        for i in xrange(lib.sqlite3_column_count(self.statement)):
            name = lib.sqlite3_column_name(self.statement, i)
            name = ffi.string(name).split("[")[0].strip()
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
        typ = lib.sqlite3_value_type(params[i])
        if typ == lib.SQLITE_INTEGER:
            val = lib.sqlite3_value_int64(params[i])
            if -sys.maxint - 1 <= val <= sys.maxint:
                val = int(val)
        elif typ == lib.SQLITE_FLOAT:
            val = lib.sqlite3_value_double(params[i])
        elif typ == lib.SQLITE_BLOB:
            blob_len = lib.sqlite3_value_bytes(params[i])
            blob = lib.sqlite3_value_blob(params[i])
            val = ffi.buffer(blob, blob_len)[:]
        elif typ == lib.SQLITE_NULL:
            val = None
        elif typ == lib.SQLITE_TEXT:
            val = lib.sqlite3_value_text(params[i])
            # XXX changed from con.text_factory
            val = unicode(val, 'utf-8')
        else:
            raise NotImplementedError
        _params.append(val)
    return _params


def _convert_result(con, val):
    if val is None:
        lib.sqlite3_result_null(con)
    elif isinstance(val, (bool, int, long)):
        lib.sqlite3_result_int64(con, int(val))
    elif isinstance(val, str):
        # XXX ignoring unicode issue
        lib.sqlite3_result_text(con, val, len(val), _SQLITE_TRANSIENT)
    elif isinstance(val, unicode):
        val = val.encode('utf-8')
        lib.sqlite3_result_text(con, val, len(val), _SQLITE_TRANSIENT)
    elif isinstance(val, float):
        lib.sqlite3_result_double(con, val)
    elif isinstance(val, buffer):
        lib.sqlite3_result_blob(con, str(val), len(val), _SQLITE_TRANSIENT)
    else:
        raise NotImplementedError


def function_callback(real_cb, context, nargs, c_params):
    params = _convert_params(context, nargs, c_params)
    try:
        val = real_cb(*params)
    except Exception:
        msg = "user-defined function raised exception"
        lib.sqlite3_result_error(context, msg, len(msg))
    else:
        _convert_result(context, val)


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

        val = datetime.datetime(year, month, day, hours, minutes, seconds,
                                microseconds)
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
