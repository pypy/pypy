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
        assert cursor.description == [
            ('NUMBERCOL', oracle.NUMBER, 127, 2, 0, 0, 1)]
        data = cursor.fetchall()
        assert data == [(1,)]
