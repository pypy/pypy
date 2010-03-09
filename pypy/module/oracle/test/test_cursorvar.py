from pypy.module.oracle.test.test_connect import OracleTestBase

class AppTestCursorVar(OracleTestBase):

    def test_bind_inout(self):
        cur = self.cnx.cursor()
        cursor = self.cnx.cursor()
        assert cursor.description is None
        cur.execute("""
            begin
              open :cursor for select 1 numbercol from dual;
            end;""",
            cursor=cursor)
        assert (cursor.description ==
                [('NUMBERCOL', oracle.NUMBER, 127, 2, 0, 0, 1)]
                or cursor.description ==
                [('NUMBERCOL', oracle.NUMBER, 127, 2, 0, -127, 1)])
        data = cursor.fetchall()
        assert data == [(1,)]

    def test_bind_frompackage(self):
        cur = self.cnx.cursor()
        # create package
        try:
            cur.execute("drop package pypy_temp_cursorpkg")
        except oracle.DatabaseError:
            pass
        cur.execute("""
            create package pypy_temp_cursorpkg as
                type refcur is ref cursor;
                procedure test_cursor(cur out refcur);
            end;""")
        cur.execute("""
            create package body pypy_temp_cursorpkg as
                procedure test_cursor(cur out refcur) is
                begin
                    open cur for
                      select level-1 intcol
                      from dual connect by level-1<42;
                end;
            end;""")
        cursor = self.cnx.cursor()
        cur.callproc("pypy_temp_cursorpkg.test_cursor", (cursor,))
        data = cursor.fetchall()
        assert data == [(x,) for x in range(42)]
