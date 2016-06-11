import py
import os, sys
import re, array, struct
from rpython.tool.udir import udir
from rpython.translator.interactive import Translation
from rpython.rlib.rarithmetic import LONG_BIT
from rpython.rlib import revdb
"""
These tests require pexpect (UNIX-only).
http://pexpect.sourceforge.net/
"""
import pexpect


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


def compile(self, entry_point, argtypes, backendopt=True):
    t = Translation(entry_point, None, gc="boehm")
    self.t = t
    t.config.translation.reverse_debugger = True
    t.config.translation.rweakref = False
    t.config.translation.lldebug0 = True
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


class BaseTests(object):
    compile = compile
    run = run
    fetch_rdb = fetch_rdb


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


class InteractiveTests(object):
    EOF = pexpect.EOF

    def replay(self, **kwds):
        kwds.setdefault('timeout', 10)
        child = pexpect.spawn(str(self.exename),
                              ['--replay', str(self.rdbname)], **kwds)
        child.logfile = sys.stdout
        def expectx(s):
            child.expect(re.escape(s))
        assert not hasattr(child, 'expectx')
        child.expectx = expectx
        return child


class TestSimpleInterpreter(InteractiveTests):

    def setup_class(cls):
        def main(argv):
            for op in argv[1:]:
                revdb.stop_point(42)
                print op
            return 9
        compile(cls, main, [], backendopt=False)
        assert run(cls, 'abc d ef') == 'abc\nd\nef\n'
        assert fetch_rdb(cls).number_of_stop_points() == 3

    def test_go(self):
        child = self.replay()
        child.expectx('stop_points=3\r\n')
        child.expectx('(3)$ ')
        child.sendline('go 1')
        child.expectx('(1)$ ')
        child.sendline('')
        child.expectx('(1)$ ')
        child.sendline('go 52')
        child.expectx('(3)$ ')

    def test_help(self):
        child = self.replay()
        child.sendline('help')
        child.expectx('select command:\r\n')
        # ...
        child.expectx('(3)$ ')
        child.sendline('info')
        child.expectx("bad category '', try 'help'\r\n")

    def test_info_fork(self):
        child = self.replay()
        child.sendline('info fork')
        child.expectx('latest_fork=3\r\n')

    def test_quit(self):
        child = self.replay()
        child.sendline('quit')
        child.expect(self.EOF)

    def test_forward(self):
        child = self.replay()
        child.sendline('go 1')
        child.expectx('(1)$ ')
        child.sendline('forward 1')
        child.expectx('(2)$ ')
        child.sendline('forward 1')
        child.expectx('(3)$ ')
        child.sendline('info fork')
        child.expectx('latest_fork=1\r\n')
        child.sendline('forward 1')
        child.expectx('At end.\r\n')
        child.expectx('(3)$ ')
        child.sendline('info fork')
        child.expectx('latest_fork=3\r\n')
