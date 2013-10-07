# -*- coding: utf-8 -*-
"""Tests for _sqlite3.py"""

import pytest, sys

if sys.version_info < (2, 7):
    pytest.skip("_sqlite3 requires Python 2.7")
try:
    import _cffi_backend
except ImportError:
    # On CPython, "pip install cffi".  On old PyPy's, no chance
    pytest.skip("_sqlite3 requires _cffi_backend to be installed")

from lib_pypy import _sqlite3

def pytest_funcarg__con(request):
    con = _sqlite3.connect(':memory:')
    request.addfinalizer(lambda: con.close())
    return con

def test_list_ddl(con):
    """From issue996.  Mostly just looking for lack of exceptions."""
    cursor = con.cursor()
    cursor.execute('CREATE TABLE foo (bar INTEGER)')
    result = list(cursor)
    assert result == []
    cursor.execute('INSERT INTO foo (bar) VALUES (42)')
    result = list(cursor)
    assert result == []
    cursor.execute('SELECT * FROM foo')
    result = list(cursor)
    assert result == [(42,)]

def test_connect_takes_same_positional_args_as_Connection(con):
    from inspect import getargspec
    clsargs = getargspec(_sqlite3.Connection.__init__).args[1:]  # ignore self
    conargs = getargspec(_sqlite3.connect).args
    assert clsargs == conargs

def test_total_changes_after_close(con):
    con.close()
    pytest.raises(_sqlite3.ProgrammingError, "con.total_changes")

def test_connection_check_init():
    class Connection(_sqlite3.Connection):
        def __init__(self, name):
            pass

    con = Connection(":memory:")
    e = pytest.raises(_sqlite3.ProgrammingError, "con.cursor()")
    assert '__init__' in e.value.message

def test_cursor_check_init(con):
    class Cursor(_sqlite3.Cursor):
        def __init__(self, name):
            pass

    cur = Cursor(con)
    e = pytest.raises(_sqlite3.ProgrammingError, "cur.execute('select 1')")
    assert '__init__' in e.value.message

def test_connection_after_close(con):
    pytest.raises(TypeError, "con()")
    con.close()
    # raises ProgrammingError because should check closed before check args
    pytest.raises(_sqlite3.ProgrammingError, "con()")

def test_cursor_iter(con):
    cur = con.cursor()
    with pytest.raises(StopIteration):
        next(cur)

    cur.execute('select 1')
    next(cur)
    with pytest.raises(StopIteration):
        next(cur)

    cur.execute('select 1')
    con.commit()
    next(cur)
    with pytest.raises(StopIteration):
        next(cur)

    with pytest.raises(_sqlite3.ProgrammingError):
        cur.executemany('select 1', [])
    with pytest.raises(StopIteration):
        next(cur)

    cur.execute('select 1')
    cur.execute('create table test(ing)')
    with pytest.raises(StopIteration):
        next(cur)

    cur.execute('select 1')
    cur.execute('insert into test values(1)')
    con.commit()
    with pytest.raises(StopIteration):
        next(cur)

def test_cursor_after_close(con):
    cur = con.execute('select 1')
    cur.close()
    con.close()
    pytest.raises(_sqlite3.ProgrammingError, "cur.close()")
    # raises ProgrammingError because should check closed before check args
    pytest.raises(_sqlite3.ProgrammingError, "cur.execute(1,2,3,4,5)")
    pytest.raises(_sqlite3.ProgrammingError, "cur.executemany(1,2,3,4,5)")

@pytest.mark.skipif("not hasattr(sys, 'pypy_translation_info')")
def test_connection_del(tmpdir):
    """For issue1325."""
    import os
    import gc
    try:
        import resource
    except ImportError:
        pytest.skip("needs resource module")

    limit = resource.getrlimit(resource.RLIMIT_NOFILE)
    try:
        fds = 0
        while True:
            fds += 1
            resource.setrlimit(resource.RLIMIT_NOFILE, (fds, limit[1]))
            try:
                for p in os.pipe(): os.close(p)
            except OSError:
                assert fds < 100
            else:
                break
        def open_many(cleanup):
            con = []
            for i in range(3):
                con.append(_sqlite3.connect(str(tmpdir.join('test.db'))))
                if cleanup:
                    con[i] = None
                    gc.collect(); gc.collect()

        pytest.raises(_sqlite3.OperationalError, open_many, False)
        gc.collect(); gc.collect()
        open_many(True)
    finally:
        resource.setrlimit(resource.RLIMIT_NOFILE, limit)

def test_on_conflict_rollback_executemany(con):
    major, minor, micro = _sqlite3.sqlite_version.split('.')[:3]
    if (int(major), int(minor), int(micro)) < (3, 2, 2):
        pytest.skip("requires sqlite3 version >= 3.2.2")
    con.execute("create table foo(x, unique(x) on conflict rollback)")
    con.execute("insert into foo(x) values (1)")
    try:
        con.executemany("insert into foo(x) values (?)", [[1]])
    except _sqlite3.DatabaseError:
        pass
    con.execute("insert into foo(x) values (2)")
    try:
        con.commit()
    except _sqlite3.OperationalError:
        pytest.fail("_sqlite3 knew nothing about the implicit ROLLBACK")

def test_statement_arg_checking(con):
    with pytest.raises(_sqlite3.Warning) as e:
        con(123)
    assert str(e.value) == 'SQL is of wrong type. Must be string or unicode.'
    with pytest.raises(ValueError) as e:
        con.execute(123)
    assert str(e.value) == 'operation parameter must be str or unicode'
    with pytest.raises(ValueError) as e:
        con.executemany(123, 123)
    assert str(e.value) == 'operation parameter must be str or unicode'
    with pytest.raises(ValueError) as e:
        con.executescript(123)
    assert str(e.value) == 'script argument must be unicode or string.'

def test_statement_param_checking(con):
    con.execute('create table foo(x)')
    con.execute('insert into foo(x) values (?)', [2])
    con.execute('insert into foo(x) values (?)', (2,))
    class seq(object):
        def __len__(self):
            return 1
        def __getitem__(self, key):
            return 2
    con.execute('insert into foo(x) values (?)', seq())
    del seq.__len__
    with pytest.raises(_sqlite3.ProgrammingError):
        con.execute('insert into foo(x) values (?)', seq())
    with pytest.raises(_sqlite3.ProgrammingError):
        con.execute('insert into foo(x) values (?)', {2:2})
    with pytest.raises(ValueError) as e:
        con.execute('insert into foo(x) values (?)', 2)
    assert str(e.value) == 'parameters are of unsupported type'

def test_explicit_begin(con):
    con.execute('BEGIN')
    con.execute('BEGIN ')
    con.execute('BEGIN')
    con.commit()
    con.execute('BEGIN')
    con.commit()

def test_row_factory_use(con):
    con.row_factory = 42
    con.execute('select 1')

def test_returning_blob_must_own_memory(con):
    import gc
    con.create_function("returnblob", 0, lambda: buffer("blob"))
    cur = con.execute("select returnblob()")
    val = cur.fetchone()[0]
    for i in range(5):
        gc.collect()
        got = (val[0], val[1], val[2], val[3])
        assert got == ('b', 'l', 'o', 'b')
    # in theory 'val' should be a read-write buffer
    # but it's not right now
    pytest.skip("in theory 'val' should be a read-write buffer")
    val[1] = 'X'
    got = (val[0], val[1], val[2], val[3])
    assert got == ('b', 'X', 'o', 'b')

def test_description_after_fetchall(con):
    cur = con.cursor()
    cur.execute("select 42").fetchall()
    assert cur.description is not None

def test_executemany_lastrowid(con):
    cur = con.cursor()
    cur.execute("create table test(a)")
    cur.executemany("insert into test values (?)", [[1], [2], [3]])
    assert cur.lastrowid is None

def test_issue1573(con):
    cur = con.cursor()
    cur.execute(u'SELECT 1 as méil')
    assert cur.description[0][0] == u"méil".encode('utf-8')

def test_adapter_exception(con):
    def cast(obj):
        raise ZeroDivisionError

    _sqlite3.register_adapter(int, cast)
    try:
        cur = con.cursor()
        cur.execute("select ?", (4,))
        val = cur.fetchone()[0]
        # Adapter error is ignored, and parameter is passed as is.
        assert val == 4
        assert type(val) is int
    finally:
        del _sqlite3.adapters[(int, _sqlite3.PrepareProtocol)]
