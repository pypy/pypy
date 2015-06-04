import errno

class AppTestErrno:
    spaceconfig = dict(usemodules=['errno'])

    def setup_class(cls): 
        cls.w_errno = cls.space.appexec([], "(): import errno ; return errno")
        cls.w_errorcode = cls.space.wrap(errno.errorcode)

    def test_posix(self):
        assert not hasattr(self.errno, '__file__')

    def test_constants(self):
        host_errorcode = self.errorcode.copy()
        # On some systems, ENOTSUP is an alias to EOPNOTSUPP.  Adjust the
        # host_errorcode dictionary in case the host interpreter has slightly
        # different errorcodes than the interpreter under test
        if ('ENOTSUP' not in host_errorcode.values() and
            'ENOTSUP' in self.errno.errorcode.values()):
            host_errorcode[self.errno.ENOTSUP] = 'ENOTSUP'
        if ('EOPNOTSUPP' not in host_errorcode.values() and
            'EOPNOTSUPP' in self.errno.errorcode.values()):
            host_errorcode[self.errno.EOPNOTSUPP] = 'EOPNOTSUPP'
        for code, name in host_errorcode.items():
            assert getattr(self.errno, name) == code

    def test_errorcode(self):
        host_errorcode = self.errorcode.copy()
        # On some systems, ENOTSUP is an alias to EOPNOTSUPP.  Adjust the
        # host_errorcode dictionary in case the host interpreter has slightly
        # different errorcodes than the interpreter under test
        if ('ENOTSUP' not in host_errorcode.values() and
            'ENOTSUP' in self.errno.errorcode.values()):
            host_errorcode[self.errno.ENOTSUP] = 'ENOTSUP'
        if ('EOPNOTSUPP' not in host_errorcode.values() and
            'EOPNOTSUPP' in self.errno.errorcode.values()):
            host_errorcode[self.errno.EOPNOTSUPP] = 'EOPNOTSUPP'
        assert host_errorcode == self.errno.errorcode
