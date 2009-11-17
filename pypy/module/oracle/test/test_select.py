from pypy.module.oracle.test.test_connect import OracleTestBase

class AppTestSelect(OracleTestBase):

    def test_fetchone(self):
        cur = self.cnx.cursor()
        cur.execute("select 42, 'Hello' from dual")
        row = cur.fetchone()
        assert isinstance(row[0], float)
        assert isinstance(row[1], str)
        assert row == (42, 'Hello')

    def test_sysdate(self):
        import datetime
        cur = self.cnx.cursor()
        cur.execute("select sysdate from dual")
        row = cur.fetchone()
        sysdate = row[0]
        assert isinstance(sysdate, datetime.datetime)
        delta = abs(sysdate - datetime.datetime.now())
        assert delta < datetime.timedelta(seconds=2)
        
    def test_fetchall(self):
        cur = self.cnx.cursor()
        # An Oracle trick to retrieve 42 lines
        cur.execute("select level-1 from dual connect by level-1<42")
        rows = cur.fetchall()
        assert rows == zip(range(42))

    def test_iterator(self):
        cur = self.cnx.cursor()
        # An Oracle trick to retrieve 42 lines
        cur.execute("select level-1 from dual connect by level-1<42")
        for i, row in enumerate(cur):
            assert row == (i,)
        assert i == 41

        
