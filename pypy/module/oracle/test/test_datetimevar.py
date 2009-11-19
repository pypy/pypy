from pypy.module.oracle.test.test_connect import OracleTestBase

class AppTestDatetime(OracleTestBase):

    def test_bind_datetime(self):
        import datetime
        cur = self.cnx.cursor()
        cur.execute("select to_char(:d, 'YYYYMMDD-HH24MISS') from dual",
                    d=datetime.datetime(2002, 12, 13, 9, 36, 15))
        data = cur.fetchall()
        assert data == [('20021213-093615',)]

    def test_bind_date(self):
        import datetime
        cur = self.cnx.cursor()
        cur.execute("select to_char(:d, 'YYYYMMDD-HH24MISS') from dual",
                    d=datetime.date(2002, 12, 13))
        data = cur.fetchall()
        assert data == [('20021213-000000',)]

