import py
import os, sys
import re, array, struct
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

    def number_of_stop_points(self):
        return struct.unpack_from("q", self.buffer, len(self.buffer) - 8)[0]

    def done(self):
        return self.cur == len(self.buffer)


class BaseTests(object):

    def compile(self, entry_point, argtypes, backendopt=True):
        t = Translation(entry_point, None, gc="boehm")
        self.t = t
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

    def run(self, *argv):
        env = os.environ.copy()
        env['PYPYREVDB'] = self.rdbname
        t = self.t
        stdout, stderr = t.driver.cbuilder.cmdexec(' '.join(argv), env=env,
                                                   expect_crash=9)
        print >> sys.stderr, stderr
        return stdout

    def fetch_rdb(self):
        return RDB(self.rdbname)


class TestRecording(BaseTests):

    def test_simple(self):
        def main(argv):
            print argv[1:]
            return 9
        self.compile(main, [], backendopt=False)
        assert self.run('abc d') == '[abc, d]\n'
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
        x = rdb.next('q'); assert x == 0      # number of stop points
        # that's all we should get from this simple example
        assert rdb.done()
        #
        assert got == [self.exename, 'abc', 'd']


class TestInteraction(BaseTests):
    """
    These tests require pexpect (UNIX-only).
    http://pexpect.sourceforge.net/
    """
    def replay(self, **kwds):
        import pexpect
        self.EOF = pexpect.EOF
        kwds.setdefault('timeout', 10)
        child = pexpect.spawn(str(self.exename),
                              ['--replay', str(self.rdbname)], **kwds)
        child.logfile = sys.stdout
        return child

    def test_simple_interpreter(self):
        def main(argv):
            for op in argv[1:]:
                revdb.stop_point(42)
                print op
            return 9
        self.compile(main, [], backendopt=False)
        assert self.run('abc d ef') == 'abc\nd\nef\n'
        assert self.fetch_rdb().number_of_stop_points() == 3

        child = self.replay()

        def wait(s):
            child.expect(re.escape(s))

        wait('stop_points=3\r\n')
        wait('(3)$ ')
        child.sendline('go 1')
        wait('(1)$ ')
        child.sendline('')
        wait('(1)$ ')
        child.sendline('go 52')
        wait('(3)$ ')
        child.sendline('help')
        wait('select command:\r\n')
        # ...
        wait('(3)$ ')
        child.sendline('info')
        wait("bad category '', try 'help'\r\n")
        child.sendline('info fork')
        wait('latest_fork=3\r\n')
        child.sendline('quit')
        child.expect(self.EOF)
