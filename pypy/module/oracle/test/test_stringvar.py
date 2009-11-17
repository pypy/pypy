from pypy.module.oracle.test.test_connect import OracleTestBase

class AppTestStringVar(OracleTestBase):

    def test_rowid(self):
        cur = self.cnx.cursor()
        var = cur.var(oracle.NUMBER)
        cur.execute("select rowid from dual")
        rowid, = cur.fetchone()
        cur.execute("select * from dual where rowid = :r",
                    r=rowid)
        cur.fetchall()
        assert cur.rowcount == 1

