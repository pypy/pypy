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
                    d=oracle.Date(2002, 12, 13))
        data = cur.fetchall()
        assert data == [('20021213-000000',)]

    def test_variable_datetime(self):
        import datetime
        cur = self.cnx.cursor()
        var = cur.var(oracle.DATETIME)
        value = datetime.datetime(2002, 12, 13, 9, 36, 15)
        var.setvalue(0, value)
        assert var.getvalue() == value

        value = datetime.date(2002, 12, 13)
        var.setvalue(0, value)
        assert var.getvalue() == datetime.datetime(2002, 12, 13)

    def test_variable_date(self):
        import datetime
        cur = self.cnx.cursor()
        var = cur.var(oracle.DATE)
        value = datetime.date(2002, 12, 13)
        var.setvalue(0, value)
        assert var.getvalue() == value

        var.setvalue(0, datetime.datetime(2002, 12, 13, 9, 36, 15))
        assert var.getvalue() == value

    def test_arrayvar(self):
        import datetime
        cur = self.cnx.cursor()
        var = cur.arrayvar(oracle.DATETIME, 2)
        values = [datetime.datetime(2002, 12, 13, 9, 36, 15),
                  datetime.datetime(2003,  7, 22, 4, 24, 32)]
        var.setvalue(0, values)
        assert var.getvalue() == values
