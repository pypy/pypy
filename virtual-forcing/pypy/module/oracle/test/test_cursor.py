from pypy.module.oracle.test.test_connect import OracleTestBase

class AppTestCursor(OracleTestBase):

    def test_attributes(self):
        cur = self.cnx.cursor()
        stmt = "select 1 from dual"
        cur.execute(stmt)
        assert cur.rowcount == 0
        cur.fetchall()
        assert cur.rowcount == 1
        assert cur.statement == stmt

    def test_bindNames(self):
        cur = self.cnx.cursor()
        raises(oracle.ProgrammingError, cur.bindnames)
        cur.prepare("begin null; end;")
        assert cur.bindnames() == []
        cur.prepare("begin :retval := :inval + 5; end;")
        assert cur.bindnames() == ["RETVAL", "INVAL"]
        cur.prepare("begin :retval := :a * :a + :b * :b; end;")
        assert cur.bindnames() == ["RETVAL", "A", "B"]
        cur.prepare("begin :a := :b + :c + :d + :e + :f + :g + "
                    ":h + :i + :j + :k + :l; end;")
        assert cur.bindnames() == ["A", "B", "C", "D", "E", "F",
                                   "G", "H", "I", "J", "K", "L"]

    def test_var(self):
        cur = self.cnx.cursor()
        cur.var(oracle.NUMBER)
        raises(TypeError, cur.var, 0)

    def test_bind_out(self):
        cur = self.cnx.cursor()
        var = cur.var(oracle.NUMBER)
        var.setvalue(0, 5)
        assert var.getvalue(0) == 5
        assert var.getvalue() == 5
        cur.execute("begin :1 := 3; end;", (var,))
        value = var.getvalue(0)
        assert value == 3
        assert isinstance(value, float)

    def test_execute_with_keywords(self):
        cur = self.cnx.cursor()
        simpleVar = cur.var(oracle.NUMBER)
        cur.execute("begin :p := 5; end;", p=simpleVar)
        assert simpleVar.getvalue() == 5

    def test_callFunc0(self):
        cur = self.cnx.cursor()
        try:
            cur.execute("drop function pypy_temp_function")
        except oracle.DatabaseError:
            pass
        cur.execute("create function pypy_temp_function "
                    "return number as "
                    "begin return 42; end;")
        assert cur.callfunc("pypy_temp_function",
                            oracle.NUMBER) == 42

    def test_callFunc1(self):
        cur = self.cnx.cursor()
        try:
            cur.execute("drop function pypy_temp_function")
        except oracle.DatabaseError:
            pass
        cur.execute("create function pypy_temp_function "
                    "(x varchar2, y number) return number as "
                    "begin return length(x) + y; end;")
        res = cur.callfunc("pypy_temp_function",
                            oracle.NUMBER, ("Hi", 5))
        assert res == 7

    def test_callproc(self):
        cur = self.cnx.cursor()
        var = cur.var(oracle.NUMBER)
        try:
            cur.execute("drop procedure pypy_temp_procedure")
        except oracle.DatabaseError:
            pass
        cur.execute("create procedure pypy_temp_procedure "
                    "(x varchar2, y in out number, z out number) as "
                    "begin "
                    "  y := 10;"
                    "  z := 2;"
                    "end;")
        results = cur.callproc("pypy_temp_procedure", ("hi", 5, var))
        assert results == ["hi", 10, 2.0]

    def test_callproc_noargs(self):
        cur = self.cnx.cursor()
        try:
            cur.execute("drop procedure pypy_temp_procedure")
        except oracle.DatabaseError:
            pass
        cur.execute("create procedure pypy_temp_procedure as "
                    "begin null; end;")
        results = cur.callproc("pypy_temp_procedure", ())
        assert results == []
        results = cur.callproc("pypy_temp_procedure")
        assert results == []

    def test_executemany_bypos(self):
        cur = self.cnx.cursor()
        try:
            cur.execute("drop table pypy_temp_table")
        except oracle.DatabaseError:
            pass
        cur.execute("create table pypy_temp_table (intcol number)")
        rows = [ [n] for n in range(23) ]
        cur.arraysize = 10
        statement = "insert into pypy_temp_table (intcol) values (:1)"
        cur.executemany(statement, rows)
        cur.execute("select count(*) from pypy_temp_table")
        count, = cur.fetchone()
        assert count == len(rows)

    def test_executemany_byname(self):
        cur = self.cnx.cursor()
        try:
            cur.execute("drop table pypy_temp_table")
        except oracle.DatabaseError:
            pass
        cur.execute("create table pypy_temp_table (intcol number)")
        rows = [ { "value" : n } for n in range(23) ]
        cur.arraysize = 10
        statement = "insert into pypy_temp_table (intcol) values (:value)"
        cur.executemany(statement, rows)
        cur.execute("select count(*) from pypy_temp_table")
        count, = cur.fetchone()
        assert count == len(rows)

    def test_executemany_withresize(self):
        cur = self.cnx.cursor()
        try:
            cur.execute("drop table pypy_temp_table")
        except oracle.DatabaseError:
            pass
        cur.execute("create table pypy_temp_table"
                    "(intcol number, stringcol varchar2(10))")
        rows = [ ( 1, "First" ),
                 ( 2, "Second" ),
                 ( 3, "Third" ),
                 ( 4, "Fourth" ),
                 ( 5, "Fifth" ),
                 ( 6, "Sixth" ),
                 ( 7, "Seventh" ) ]
        cur.bindarraysize = 5
        cur.setinputsizes(int, 100)
        sql = "insert into pypy_temp_table (intcol, stringcol) values (:1, :2)"
        cur.executemany(sql, rows)
        var = cur.bindvars[1]
        cur.execute("select count(*) from pypy_temp_table")
        count, = cur.fetchone()
        assert count == len(rows)
        assert var.maxlength == 100 * self.cnx.maxBytesPerCharacter

    def test_description_number(self):
        cur = self.cnx.cursor()
        try:
            cur.execute("drop table pypy_temp_table")
        except oracle.DatabaseError:
            pass
        cur.execute("create table pypy_temp_table ("
                    "intcol                number(9) not null,"
                    "numbercol             number(9, 2) not null,"
                    "floatcol              float not null,"
                    "unconstrainedcol      number not null,"
                    "nullablecol           number(38)"
                    ")")
        cur.execute("select * from pypy_temp_table")
        got = cur.description
        expected = [
            ('INTCOL', oracle.NUMBER, 10, 22, 9, 0, 0),
            ('NUMBERCOL', oracle.NUMBER, 13, 22, 9, 2, 0),
            ('FLOATCOL', oracle.NUMBER, 127, 22, 126, -127, 0),
            ('UNCONSTRAINEDCOL', oracle.NUMBER, 127, 22, 0, -127, 0),
            ('NULLABLECOL', oracle.NUMBER, 39, 22, 38, 0, 1),
            ]
        assert got == expected

    def test_outputsize(self):
        cur = self.cnx.cursor()
        cur.setoutputsize(25000)
        cur.setoutputsize(25000, 2)
