from pypy.module.oracle.test.test_connect import OracleTestBase

class AppTestNumberVar(OracleTestBase):

    def test_float(self):
        cur = self.cnx.cursor()
        var = cur.var(oracle.NUMBER)
        cur.execute("begin :a := :b*2.5; end;", a=var,
                    b=0.5)
        assert var.getvalue() == 1.25

    def test_decimal(self):
        import decimal
        cur = self.cnx.cursor()
        var = cur.var(oracle.NUMBER)
        cur.execute("begin :a := :b*2.5; end;", a=var,
                    b=decimal.Decimal("0.5"))
        assert var.getvalue() == 1.25
