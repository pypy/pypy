from pypy.conftest import gettestobjspace
import py

from pypy.rpython.tool.rffi_platform import CompilationError
try:
    from pypy.module.oracle import roci
except (CompilationError, ImportError):
    py.test.skip("Oracle client not available")

class AppTestConnection:

    def setup_class(cls):
        space = gettestobjspace(usemodules=('oracle',))
        cls.space = space
        space.setitem(space.builtin.w_dict, space.wrap('oracle'),
                      space.getbuiltinmodule('cx_Oracle'))
        cls.w_username = space.wrap('cx_oracle')
        cls.w_password = space.wrap('dev')
        cls.w_tnsentry = space.wrap('xe')

    def test_connect(self):
        cnx = oracle.connect(self.username, self.password,
                             self.tnsentry, threaded=True)
        assert cnx.username == self.username
        assert cnx.password == self.password
        assert cnx.tnsentry == self.tnsentry
        assert isinstance(cnx.version, str)

    def test_singleArg(self):
        cnx = oracle.connect("%s/%s@%s" % (self.username, self.password,
                                           self.tnsentry))
        assert cnx.username == self.username
        assert cnx.password == self.password
        assert cnx.tnsentry == self.tnsentry

    def test_connect_badPassword(self):
        raises(oracle.DatabaseError, oracle.connect,
               self.username, self.password + 'X', self.tnsentry)

    def test_connect_badConnectString(self):
        raises(oracle.DatabaseError, oracle.connect,
               self.username)
        raises(oracle.DatabaseError, oracle.connect,
               self.username + "@" + self.tnsentry)
        raises(oracle.DatabaseError, oracle.connect,
               self.username + "@" + self.tnsentry + "/" + self.password)
        
    def test_exceptionOnClose(self):
        connection = oracle.connect(self.username, self.password,
                                    self.tnsentry)
        connection.close()
        raises(oracle.InterfaceError, connection.rollback)

    def test_makedsn(self):
        formatString = ("(DESCRIPTION=(ADDRESS_LIST=(ADDRESS=(PROTOCOL=TCP)"
                        "(HOST=%s)(PORT=%d)))(CONNECT_DATA=(SID=%s)))")
        args = ("hostname", 1521, "TEST")
        result = oracle.makedsn(*args)
        assert result == formatString % args

    def test_rollbackOnClose(self):
        connection = oracle.connect(self.username, self.password,
                self.tnsentry)
        cursor = connection.cursor()
        try:
            cursor.execute("drop table pypy_test_temp")
        except oracle.DatabaseError:
            pass
        cursor.execute("create table pypy_test_temp (n number)")
    
        otherConnection = oracle.connect(self.username, self.password,
                self.tnsentry)
        otherCursor = otherConnection.cursor()
        otherCursor.execute("insert into pypy_test_temp (n) values (1)")
        otherConnection.close()
        cursor.execute("select count(*) from pypy_test_temp")
        count, = cursor.fetchone()
        assert count == 0


