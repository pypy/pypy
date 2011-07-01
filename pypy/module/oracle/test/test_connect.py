from pypy.conftest import gettestobjspace
from pypy.conftest import option
from pypy.rpython.tool.rffi_platform import CompilationError
import py

class OracleNotConnectedTestBase(object):

    @classmethod
    def setup_class(cls):
        space = gettestobjspace(usemodules=('oracle',))
        cls.space = space
        space.setitem(space.builtin.w_dict, space.wrap('oracle'),
                      space.getbuiltinmodule('cx_Oracle'))
        oracle_connect = option.oracle_connect
        if not oracle_connect:
            py.test.skip(
                "Please set --oracle-connect to a valid connect string")
        usrpwd, tnsentry = oracle_connect.rsplit('@', 1)
        username, password = usrpwd.split('/', 1)
        cls.w_username = space.wrap(username)
        cls.w_password = space.wrap(password)
        cls.w_tnsentry = space.wrap(tnsentry)

class OracleTestBase(OracleNotConnectedTestBase):
    @classmethod
    def setup_class(cls):
        super(OracleTestBase, cls).setup_class()
        cls.w_cnx = cls.space.appexec(
            [cls.w_username, cls.w_password, cls.w_tnsentry],
            """(username, password, tnsentry):
                import cx_Oracle
                return cx_Oracle.connect(username, password, tnsentry)
            """)

    def teardown_class(cls):
        cls.space.call_method(cls.w_cnx, "close")

class AppTestConnection(OracleNotConnectedTestBase):

    def teardown_method(self, func):
        if hasattr(self, 'cnx'):
            self.cnx.close()

    def test_constants(self):
        assert '.' in oracle.version
        assert oracle.paramstyle == 'named'

    def test_connect(self):
        self.cnx = oracle.connect(self.username, self.password,
                                  self.tnsentry, threaded=True)
        assert self.cnx.username == self.username
        assert self.cnx.password == self.password
        assert self.cnx.tnsentry == self.tnsentry
        assert isinstance(self.cnx.version, str)

    def test_connect_twophase(self):
        self.cnx = oracle.connect(self.username, self.password,
                                  self.tnsentry, twophase=True)
        assert self.cnx.username == self.username
        assert self.cnx.password == self.password
        assert self.cnx.tnsentry == self.tnsentry

    def test_singleArg(self):
        self.cnx = oracle.connect("%s/%s@%s" % (self.username, self.password,
                                                self.tnsentry))
        assert self.cnx.username == self.username
        assert self.cnx.password == self.password
        assert self.cnx.tnsentry == self.tnsentry

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
        self.cnx = oracle.connect(self.username, self.password,
                self.tnsentry)
        cursor = self.cnx.cursor()
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

    def test_charset(self):
        self.cnx = oracle.connect(self.username, self.password,
                                  self.tnsentry)
        encoding = self.cnx.encoding
        assert isinstance(encoding, str)
        assert encoding != ""
        encoding = self.cnx.nationalencoding
        assert isinstance(encoding, str)
        assert encoding != ""


class AppTestPool(OracleNotConnectedTestBase):
    def test_pool_basicattributes(self):
        pool = oracle.SessionPool(self.username, self.password,
                                  self.tnsentry,
                                  2, 8, 3)
        assert pool.username == self.username
        assert pool.password == self.password
        assert pool.tnsentry == self.tnsentry
        assert pool.max == 8
        assert pool.min == 2
        assert pool.increment == 3
        assert pool.opened == 2
        assert pool.busy == 0

    def test_pool_acquire(self):
        pool = oracle.SessionPool(self.username, self.password,
                                  self.tnsentry,
                                  2, 8, 3)
        assert (pool.busy, pool.opened) == (0, 2)
        c1 = pool.acquire()
        assert (pool.busy, pool.opened) == (1, 2)
        c2 = pool.acquire()
        assert (pool.busy, pool.opened) == (2, 2)
        c3 = pool.acquire()
        assert (pool.busy, pool.opened) == (3, 5)
        pool.release(c3)
        assert pool.busy == 2
        del c2
        import gc; gc.collect()
        assert pool.busy == 1

    def test_proxy_auth(self):
        pool = oracle.SessionPool(self.username, self.password,
                                  self.tnsentry,
                                  2, 8, 3)
        assert pool.homogeneous is True
        raises(oracle.ProgrammingError, pool.acquire, user="proxyuser")
        pool = oracle.SessionPool(self.username, self.password,
                                  self.tnsentry,
                                  2, 8, 3, homogeneous=False)
        assert pool.homogeneous is False
        e = raises(oracle.DatabaseError, pool.acquire, user="proxyuser")
        # ORA-01017: invalid username/password; logon denied
        # ORA-28150: proxy not authorized to connect as client
        # ORA-01031: insufficient privileges
        print "Error code", e.value[0].code
        assert e.value[0].code in (1017, 28150, 1031)
