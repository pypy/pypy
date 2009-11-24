from pypy.module.oracle.test.test_connect import OracleTestBase

class AppTestNumberVar(OracleTestBase):

    def test_fetch(self):
        cur = self.cnx.cursor()
        cur.execute("select 1.5 from dual")
        value, = cur.fetchone()
        assert value == 1.5

    def test_float(self):
        cur = self.cnx.cursor()
        var = cur.var(oracle.NUMBER)
        cur.execute("begin :a := :b*2.5; end;", a=var,
                    b=0.5)
        assert var.getvalue() == 1.25

    def test_bool(self):
        cur = self.cnx.cursor()
        var = cur.var(oracle.NUMBER)
        cur.execute("begin :a := :b*2.5; end;", a=var,
                    b=True)
        assert var.getvalue() == 2.5

    def test_decimal(self):
        import decimal
        cur = self.cnx.cursor()
        var = cur.var(oracle.NUMBER)
        cur.execute("begin :a := :b*2.5; end;", a=var,
                    b=decimal.Decimal("0.5"))
        assert var.getvalue() == 1.25

    def test_largelong(self):
        cur = self.cnx.cursor()
        var = cur.var(oracle.NUMBER)
        var.setvalue(0, 6088343244)
        cur.execute("select :x+5 from dual", x=var)
        value, = cur.fetchone()
        assert value == 6088343249

    def test_smalllong(self):
        cur = self.cnx.cursor()
        cur.execute("select :x from dual", x=3L)
        value, = cur.fetchone()
        assert value == 3

