from pypy.module.oracle.test.test_connect import OracleTestBase

class AppTestObjectVar(OracleTestBase):
    def test_fetch_object(self):
        import datetime
        cur = self.cnx.cursor()
        try:
            cur.execute("drop table pypy_test_objtable")
        except oracle.DatabaseError:
            pass
        try:
            cur.execute("drop type pypy_test_objtype")
        except oracle.DatabaseError:
            pass
        try:
            cur.execute("drop type pypy_test_arraytype")
        except oracle.DatabaseError:
            pass
        cur.execute("""\
            create type pypy_test_objtype as object (
                numbercol number,
                stringcol varchar2(60),
                datecol   date);
            """)
        cur.execute("""\
            create type pypy_test_arraytype as varray(10) of number;
            """)
        cur.execute("""\
            create table pypy_test_objtable (
                objcol pypy_test_objtype,
                arraycol pypy_test_arraytype)
            """)
        cur.execute("""\
            insert into pypy_test_objtable values (
            pypy_test_objtype(1, 'someText',
                              to_date(20070306, 'YYYYMMDD')),
            pypy_test_arraytype(5, 10, null, 20))
            """)

        cur.execute("select objcol, arraycol from pypy_test_objtable")
        objValue, arrayValue = cur.fetchone()
        assert objValue.type.schema == self.cnx.username.upper()
        assert objValue.type.name == "PYPY_TEST_OBJTYPE"
        assert objValue.type.attributes[0].name == "NUMBERCOL"
        assert isinstance(arrayValue, list)
        assert arrayValue == [5, 10, None, 20]
        assert objValue.NUMBERCOL == 1
        assert objValue.STRINGCOL == "someText"
        assert objValue.DATECOL == datetime.datetime(2007, 03, 06)
        raises(AttributeError, getattr, objValue, 'OTHER')
