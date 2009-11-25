from pypy.module.oracle.test.test_connect import OracleTestBase

class AppTestObjectVar(OracleTestBase):
    def test_fetch(self):
        cur = self.cnx.cursor()
        try:
            cur.execute("drop table pypy_test_objtable")
        except oracle.DatabaseError:
            pass
        try:
            cur.execute("drop type pypy_test_objtype")
        except oracle.DatabaseError:
            pass
        cur.execute("""\
            create type pypy_test_objtype as object (
                numbercol number,
                stringcol varchar2(60),
                datecol   date);
            """)
        cur.execute("""\
            create table pypy_test_objtable (
                objcol pypy_test_objtype)
            """)
        cur.execute("""\
            insert into pypy_test_objtable values (
            pypy_test_objtype(1, 'someText',
                              to_date(20070306, 'YYYYMMDD')))
            """)

        cur.execute("select objcol from pypy_test_objtable")
        objValue, = cur.fetchone()
        assert objValue.type.schema == self.cnx.username.upper()
        assert objValue.type.name == "PYPY_TEST_OBJTYPE"
        assert objValue.type.attributes[0].name == "NUMBERCOL"
