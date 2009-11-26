from pypy.module.oracle.test.test_connect import OracleTestBase

class AppTestStringVar(OracleTestBase):

    def test_bind_inout(self):
        cur = self.cnx.cursor()
        vars = cur.setinputsizes(value=oracle.STRING)
        cur.execute("""
            begin
              :value := :value || ' output';
            end;""",
            value="input")
        assert vars["value"].getvalue() == "input output"

    def test_rowid(self):
        cur = self.cnx.cursor()
        cur.execute("select rowid from dual")
        rowid, = cur.fetchone()
        cur.execute("select * from dual where rowid = :r",
                    r=rowid)
        cur.fetchall()
        assert cur.rowcount == 1

    def test_array(self):
        cur = self.cnx.cursor()
        array = ["n%d" % d for d in range(20)]
        tablelen = cur.var(oracle.NUMBER)
        output = cur.var(oracle.STRING)
        statement = """
                declare
                  array dbms_utility.uncl_array := :array;
                begin
                  dbms_utility.table_to_comma(
                      array, :tablelen, :output);
                end;"""
        cur.execute(statement,
                    array=array,
                    tablelen=tablelen,
                    output=output)
        assert tablelen.getvalue() == 20
        assert output.getvalue() == ','.join(array)

    def test_array_bysize(self):
        cur = self.cnx.cursor()
        array = ["n%d" % d for d in range(20)]
        tablelen = cur.var(oracle.NUMBER)
        output = cur.var(oracle.STRING)
        cur.setinputsizes(array=[oracle.STRING, 10])
        statement = """
                declare
                  array dbms_utility.uncl_array := :array;
                begin
                  dbms_utility.table_to_comma(
                      array, :tablelen, :output);
                end;"""
        cur.execute(statement,
                    array=array,
                    tablelen=tablelen,
                    output=output)
        assert tablelen.getvalue() == 20
        assert output.getvalue() == ','.join(array)

    def test_arrayvar(self):
        cur = self.cnx.cursor()
        array = ["n%d" % d for d in range(20)]
        tablelen = cur.var(oracle.NUMBER)
        output = cur.var(oracle.STRING)
        arrayvar = cur.arrayvar(oracle.STRING, array)
        arrayvar.setvalue(0, array)
        statement = """
                declare
                  array dbms_utility.uncl_array := :array;
                begin
                  dbms_utility.table_to_comma(
                      array, :tablelen, :output);
                end;"""
        cur.execute(statement,
                    array=arrayvar,
                    tablelen=tablelen,
                    output=output)
        assert tablelen.getvalue() == 20
        assert output.getvalue() == ','.join(array)

    def test_arrayvar_out(self):
        cur = self.cnx.cursor()
        array = ["n%d" % d for d in range(20)]
        tablelen = cur.var(oracle.NUMBER)
        arrayvar = cur.arrayvar(oracle.STRING, 25)
        statement = """
                declare
                  array dbms_utility.uncl_array;
                begin
                  dbms_utility.comma_to_table(
                      :input, :tablelen, array);
                  :array := array;
                end;"""
        cur.execute(statement,
                    input=','.join(array),
                    tablelen=tablelen,
                    array=arrayvar)
        assert tablelen.getvalue() == 20
        # dbms_utility.comma_to_table returns a 'NULL-terminated' table
        assert arrayvar.getvalue() == array + [None]

    def test_binary(self):
        cur = self.cnx.cursor()
        try:
            cur.execute("drop table pypy_temp_table")
        except oracle.DatabaseError:
            pass
        cur.execute("create table pypy_temp_table (rawcol raw(30))")

        cur.setinputsizes(p=oracle.BINARY)
        cur.execute("insert into pypy_temp_table values (:p)",
                    p="raw string")
        cur.execute("select * from pypy_temp_table")
        data = cur.fetchall()
        assert data == [("raw string",)]

    def test_longstring(self):
        cur = self.cnx.cursor()
        output = cur.var(oracle.LONG_STRING)
        cur.execute("""
            declare
              t_Temp varchar2(10000);
            begin
              t_Temp := :bigString;
              :output := t_Temp;
            end;""",
            bigString="X" * 10000, output=output)
        assert output.getvalue() == "X" * 10000

class AppTestLongVar(OracleTestBase):

    def test_long(self):
        cur = self.cnx.cursor()
        try:
            cur.execute("drop table pypy_temp_table")
        except oracle.DatabaseError:
            pass
        cur.execute("create table pypy_temp_table (longcol long)")

        cur.setinputsizes(p=oracle.LONG_STRING)
        cur.execute("insert into pypy_temp_table values (:p)",
                    p="long string")
        cur.execute("select * from pypy_temp_table")
        data = cur.fetchall()
        assert data == [("long string",)]

class AppTestUnicode(OracleTestBase):
    def test_bind(self):
        cur = self.cnx.cursor()
        value = u"Unicode(\u3042)"
        cur.execute("select :value from dual", value=value)
        data, = cur.fetchone()
        assert data == value

    def test_large_unicode(self):
        cur = self.cnx.cursor()
        var = cur.var(oracle.UNICODE)
        value = u"1234567890" * 400
        var.setvalue(0, value)
        assert var.getvalue() == value
        value += "X"
        raises(ValueError, var.setvalue, 0, value)
