import py
import os
import array, struct
from rpython.tool.udir import udir
from rpython.translator.interactive import Translation
from rpython.rlib.rarithmetic import LONG_BIT


class RDB(object):
    def __init__(self, filename):
        with open(filename, 'rb') as f:
            self.buffer = f.read()
        #
        self.cur = 0
        x = self.next(); assert x == 0x0A424452
        x = self.next(); assert x == 0x00FF0001
        x = self.next(); assert x == 0
        x = self.next(); assert x == 0
        self.argc = self.next()
        self.argv = self.next()

    def next(self, mode='P'):
        p = self.cur
        self.cur = p + struct.calcsize(mode)
        return struct.unpack_from(mode, self.buffer, p)[0]

    def done(self):
        return self.cur == len(self.buffer)


class TestBasic(object):

    def getcompiled(self, entry_point, argtypes, backendopt=True):
        t = Translation(entry_point, None, gc="boehm")
        t.config.translation.reverse_debugger = True
        t.config.translation.rweakref = False
        if not backendopt:
            t.disable(["backendopt_lltype"])
        t.annotate()
        t.rtype()
        if t.backendopt:
            t.backendopt()
        self.exename = t.compile_c()
        self.rdbname = os.path.join(os.path.dirname(str(self.exename)),
                                    'log.rdb')

        def run(*argv):
            env = os.environ.copy()
            env['PYPYREVDB'] = self.rdbname
            stdout = t.driver.cbuilder.cmdexec(' '.join(argv), env=env)
            return stdout
        return run

    def fetch_rdb(self):
        return RDB(self.rdbname)

    def test_simple(self):
        def main(argv):
            print argv[1:]
            return 0
        fn = self.getcompiled(main, [], backendopt=False)
        assert fn('abc d') == '[abc, d]\n'
        rdb = self.fetch_rdb()
        assert rdb.argc == 3
        #
        got = []
        for i in range(3):
            rdb.next()    # this is from "p = argv[i]"
            s = []
            # first we determine the length of the "char *p"
            while True:
                c = rdb.next('c')
                if c == '\x00':
                    break
                s.append(c)
            # then we really read the "char *" and copy it into a rpy string
            # (that's why this time we don't read the final \0)
            for c1 in s:
                c2 = rdb.next('c')
                assert c2 == c1
            got.append(''.join(s))
        # write() call
        x = rdb.next(); assert x == len('[abc, d]\n')
        x = rdb.next('i'); assert x == 0      # errno
        # that's all that should get from this simple example
        assert rdb.done()
        #
        assert got == [self.exename, 'abc', 'd']
