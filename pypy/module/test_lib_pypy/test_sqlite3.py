"""Tests for _sqlite3.py"""

def test_list_ddl():
    """From issue996.  Just looking for lack of exceptions."""
    from sqlite3.dbapi2 import connect
    connection = connect(':memory:')
    cursor = connection.cursor()
    cursor.execute('CREATE TABLE foo (bar INTEGER)')
    result = list(cursor)
