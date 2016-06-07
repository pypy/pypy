import py
import os, sys
import array, struct
from rpython.tool.udir import udir
from rpython.translator.interactive import Translation
from rpython.rlib.rarithmetic import LONG_BIT
from rpython.rlib import revdb


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
            stdout, stderr = t.driver.cbuilder.cmdexec(' '.join(argv), env=env,
                                                       expect_crash=9)
            print >> sys.stderr, stderr
            return stdout

        def replay():
            stdout = t.driver.cbuilder.cmdexec("--replay '%s'" % self.rdbname)
            return stdout

        return run, replay

    def fetch_rdb(self):
        return RDB(self.rdbname)

    def test_simple(self):
        def main(argv):
            print argv[1:]
            return 9
        fn, replay = self.getcompiled(main, [], backendopt=False)
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
        x = rdb.next('i'); assert x == 9      # exitcode
        # that's all that should get from this simple example
        assert rdb.done()
        #
        assert got == [self.exename, 'abc', 'd']
        #
        # Now try the replay mode (just "doesn't crash" for now)
        out = replay()
        assert out == ("Replaying finished.\n"
                       "stop_point 0\n")

    def test_simple_interpreter(self):
        def main(argv):
            for op in argv[1:]:
                revdb.stop_point(42)
                print op
            return 9
        fn, replay = self.getcompiled(main, [], backendopt=False)
        assert fn('abc d') == 'abc\nd\n'
        out = replay()
        assert out == ("stop_point 42\n"
                       "stop_point 42\n"
                       "Replaying finished.\n"
                       "stop_point 0\n")
