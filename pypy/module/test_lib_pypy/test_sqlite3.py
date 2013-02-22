"""Tests for _sqlite3.py"""

import sys
if sys.version_info < (2, 7):
    skip("lib_pypy._sqlite3 doesn't work with python < 2.7")

def test_list_ddl():
    """From issue996.  Mostly just looking for lack of exceptions."""
    from lib_pypy._sqlite3 import connect
    connection = connect(':memory:')
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
