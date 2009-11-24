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

class AppTestTimestamp(OracleTestBase):

    def test_bind_timestamp(self):
        import datetime
        cur = self.cnx.cursor()

        value = datetime.datetime(2002, 12, 13, 9, 36, 15, 123000)
        var = cur.var(oracle.TIMESTAMP)
        var.setvalue(0, value)
        assert var.getvalue() == value

        cur.setinputsizes(value=oracle.TIMESTAMP)
        cur.execute("select :value from dual",
                    value=value)
        data = cur.fetchall()
        assert data == [(value,)]

class AppTestInterval(OracleTestBase):

    def test_bind_interval(self):
        import datetime
        cur = self.cnx.cursor()

        value = datetime.timedelta(days=5, hours=6, minutes=10, seconds=18)
        var = cur.var(oracle.INTERVAL)
        var.setvalue(0, value)
        assert var.getvalue() == value

        cur.setinputsizes(value=oracle.INTERVAL)
        cur.execute("select :value from dual",
                    value=value)
        data = cur.fetchall()
        assert data == [(value,)]
