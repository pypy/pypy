"""Tests for _sqlite3.py"""

import sys
if sys.version_info < (2, 7):
    skip("lib_pypy._sqlite3 doesn't work with python < 2.7")

import pytest
from lib_pypy import _sqlite3

def test_list_ddl():
    """From issue996.  Mostly just looking for lack of exceptions."""
    connection = _sqlite3.connect(':memory:')
    cursor = connection.cursor()
    cursor.execute('CREATE TABLE foo (bar INTEGER)')
    result = list(cursor)
    assert result == []
    cursor.execute('INSERT INTO foo (bar) VALUES (42)')
    result = list(cursor)
    assert result == []
    cursor.execute('SELECT * FROM foo')
    result = list(cursor)
    assert result == [(42,)]

def test_total_changes_after_close():
    con = _sqlite3.connect(':memory:')
    con.close()
    pytest.raises(_sqlite3.ProgrammingError, "con.total_changes")

def test_connection_check_init():
    class Connection(_sqlite3.Connection):
        def __init__(self, name):
            pass

    con = Connection(":memory:")
    e = pytest.raises(_sqlite3.ProgrammingError, "con.cursor()")
    assert '__init__' in e.value.message

def test_cursor_check_init():
    class Cursor(_sqlite3.Cursor):
        def __init__(self, name):
            pass

    con = _sqlite3.connect(":memory:")
    cur = Cursor(con)
    e = pytest.raises(_sqlite3.ProgrammingError, "cur.execute('select 1')")
    assert '__init__' in e.value.message

def test_cursor_after_close():
     con = _sqlite3.connect(':memory:')
     cur = con.execute('select 1')
     cur.close()
     con.close()
     pytest.raises(_sqlite3.ProgrammingError, "cur.close()")

@pytest.mark.skipif("not hasattr(sys, 'pypy_translation_info')")
def test_connection_del(tmpdir):
    """For issue1325."""
    import gc

    def open_many(cleanup):
        con = []
        for i in range(1024):
            con.append(_sqlite3.connect(str(tmpdir.join('test.db'))))
            if cleanup:
                con[i] = None
                gc.collect(); gc.collect()

    pytest.raises(_sqlite3.OperationalError, open_many, False)
    gc.collect(); gc.collect()
    open_many(True)
