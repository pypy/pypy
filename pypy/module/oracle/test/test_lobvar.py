from pypy.module.oracle.test.test_connect import OracleTestBase

class LobTests(object):
    @classmethod
    def setup_class(cls):
        super(LobTests, cls).setup_class()
        cls.w_lobType = cls.space.wrap(cls.lobType)

    def test_bind(self):
        inputType = getattr(oracle, self.lobType)

        cur = self.cnx.cursor()
        try:
            cur.execute("drop table pypy_temp_lobtable")
        except oracle.DatabaseError:
            pass
        cur.execute("create table pypy_temp_lobtable "
                    "(lobcol %s)" % self.lobType)

        longString = ""
        for i in range(2):
            if i > 0:
                longString += chr(65+i) * 25000

        cur.setinputsizes(lob=inputType)
        cur.execute("insert into pypy_temp_lobtable values (:lob)",
                    lob=longString)
        cur.execute("select lobcol from pypy_temp_lobtable")
        lob, = cur.fetchone()
        assert lob.size() == len(longString)
        assert lob.read() == longString

class AppTestLob(LobTests, OracleTestBase):
    lobType = "BLOB"
