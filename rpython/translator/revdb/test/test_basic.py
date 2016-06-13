import py
import os, sys
import re, array, struct
from rpython.tool.udir import udir
from rpython.translator.interactive import Translation
from rpython.rlib.rarithmetic import LONG_BIT
from rpython.rlib import objectmodel, revdb
from rpython.rlib.rarithmetic import intmask
"""
These tests require pexpect (UNIX-only).
http://pexpect.sourceforge.net/
"""
import pexpect


class RDB(object):
    def __init__(self, filename, expected_argv):
        with open(filename, 'rb') as f:
            header = f.readline()
            self.buffer = f.read()
        assert header == 'RevDB: ' + ' '.join(expected_argv) + '\n'
        #
        self.cur = 0
        x = self.next('c'); assert x == '\x00'
        x = self.next(); assert x == 0x00FF0001
        x = self.next(); assert x == 0
        x = self.next(); assert x == 0
        self.argc = self.next()
        self.argv = self.next()
        self.read_check_argv(expected_argv)

    def next(self, mode='P'):
        p = self.cur
        self.cur = p + struct.calcsize(mode)
        return struct.unpack_from(mode, self.buffer, p)[0]

    def read_check_argv(self, expected):
        assert self.argc == len(expected)
        for i in range(self.argc):
            self.next()    # this is from "p = argv[i]"
            s = []
            # first we determine the length of the "char *p"
            while True:
                c = self.next('c')
                if c == '\x00':
                    break
                s.append(c)
            # then we really read the "char *" and copy it into a rpy string
            # (that's why this time we don't read the final \0)
            for c1 in s:
                c2 = self.next('c')
                assert c2 == c1
            assert ''.join(s) == expected[i]

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
    env['PYPYRDB'] = self.rdbname
    t = self.t
    stdout, stderr = t.driver.cbuilder.cmdexec(' '.join(argv), env=env,
                                               expect_crash=9)
    print >> sys.stderr, stderr
    return stdout

def fetch_rdb(self, expected_argv):
    return RDB(self.rdbname, map(str, expected_argv))


class TestRecording(object):
    compile = compile
    run = run
    fetch_rdb = fetch_rdb

    def test_simple(self):
        def main(argv):
            print argv[1:]
            return 9
        self.compile(main, [], backendopt=False)
        assert self.run('abc d') == '[abc, d]\n'
        rdb = self.fetch_rdb([self.exename, 'abc', 'd'])
        # write() call
        x = rdb.next(); assert x == len('[abc, d]\n')
        x = rdb.next('i'); assert x == 0      # errno
        x = rdb.next('q'); assert x == 0      # number of stop points
        # that's all we should get from this simple example
        assert rdb.done()

    def test_identityhash(self):
        def main(argv):
            print [objectmodel.compute_identity_hash(argv),
                   objectmodel.compute_identity_hash(argv),
                   objectmodel.compute_identity_hash(argv)]
            return 9
        self.compile(main, [], backendopt=False)
        out = self.run('Xx')
        match = re.match(r'\[(-?\d+), \1, \1]\n', out)
        assert match
        hash_value = int(match.group(1))
        rdb = self.fetch_rdb([self.exename, 'Xx'])
        # compute_identity_hash() call, but only the first one
        x = rdb.next(); assert intmask(x) == intmask(hash_value)
        # write() call
        x = rdb.next(); assert x == len(out)
        x = rdb.next('i'); assert x == 0      # errno
        # done
        x = rdb.next('q'); assert x == 0      # number of stop points
        assert rdb.done()

    def test_dont_record_vtable_reads(self):
        class A(object):
            x = 42
        class B(A):
            x = 43
        lst = [A(), B()]
        def main(argv):
            print lst[len(argv) & 1].x
            return 9
        self.compile(main, [], backendopt=False)
        out = self.run('Xx')
        assert out == '42\n'
        rdb = self.fetch_rdb([self.exename, 'Xx'])
        # write() call (it used to be the case that vtable reads where
        # recorded too; the single byte fetched from the vtable from
        # the '.x' in main() would appear here)
        x = rdb.next(); assert x == len(out)
        x = rdb.next('i'); assert x == 0      # errno
        # done
        x = rdb.next('q'); assert x == 0      # number of stop points
        assert rdb.done()

    def test_dont_record_pbc_reads(self):
        class MyPBC:
            def _freeze_(self):
                return True
        pbc1 = MyPBC(); pbc1.x = 41
        pbc2 = MyPBC(); pbc2.x = 42
        lst = [pbc1, pbc2]
        def main(argv):
            print lst[len(argv) & 1].x
            return 9
        self.compile(main, [], backendopt=False)
        out = self.run('Xx')
        assert out == '41\n'
        rdb = self.fetch_rdb([self.exename, 'Xx'])
        # write() call
        x = rdb.next(); assert x == len(out)
        x = rdb.next('i'); assert x == 0      # errno
        # done
        x = rdb.next('q'); assert x == 0      # number of stop points
        assert rdb.done()


class InteractiveTests(object):
    EOF = pexpect.EOF

    def replay(self, **kwds):
        kwds.setdefault('timeout', 10)
        child = pexpect.spawn(str(self.exename),
                              ['--revdb-replay', str(self.rdbname)], **kwds)
        child.logfile = sys.stdout
        def expectx(s):
            child.expect(re.escape(s))
        assert not hasattr(child, 'expectx')
        child.expectx = expectx
        return child


class TestSimpleInterpreter(InteractiveTests):

    def setup_class(cls):
        def main(argv):
            lst = [argv[0], 'prebuilt']
            for op in argv[1:]:
                revdb.stop_point()
                print op
                lst.append(op + '??')   # create a new string here
            for x in lst:
                print revdb.creation_time_of(x)
            return 9
        compile(cls, main, [], backendopt=False)
        assert run(cls, 'abc d ef') == 'abc\nd\nef\n0\n0\n1\n2\n3\n'
        rdb = fetch_rdb(cls, [cls.exename, 'abc', 'd', 'ef'])
        assert rdb.number_of_stop_points() == 3

    def test_go(self):
        child = self.replay()
        child.expectx('stop_points=3\r\n'
                      '(3)$ ')
        child.sendline('__go 1')
        child.expectx('(1)$ ')
        child.sendline('')
        child.expectx('(1)$ ')
        child.sendline('__go 52')
        child.expectx('(3)$ ')

    def test_help(self):
        child = self.replay()
        child.sendline('help')
        child.expectx('select command:\r\n')
        # ...
        child.expectx('(3)$ ')
        child.sendline('info')
        child.expectx("info ?=-1\r\n")

    def test_info_fork(self):
        child = self.replay()
        child.sendline('info fork')
        child.expectx('info f=3\r\n')

    def test_quit(self):
        child = self.replay()
        child.sendline('quit')
        child.expect(self.EOF)

    def test_forward(self):
        child = self.replay()
        child.sendline('__go 1')
        child.expectx('(1)$ ')
        child.sendline('__forward 1')
        child.expectx('(2)$ ')
        child.sendline('__forward 1')
        child.expectx('(3)$ ')
        child.sendline('info fork')
        child.expectx('info f=1\r\n')
        child.sendline('__forward 1')
        child.expectx('At end.\r\n'
                      '(3)$ ')
        child.sendline('info fork')
        child.expectx('info f=3\r\n')


class TestDebugCommands(InteractiveTests):

    def setup_class(cls):
        #
        def g(cmdline):
            if len(cmdline) > 5:
                raise ValueError
        g._dont_inline_ = True
        #
        def went_fw(arg):
            revdb.send_output('went-fw %s -> %d\n' % (arg,
                                                      revdb.current_time()))
            if revdb.current_time() != revdb.total_time():
                revdb.go_forward(1, went_fw, "yy")
        def changed_time(arg):
            revdb.send_output('changed-time %s -> %d\n' % (arg,
                                                      revdb.current_time()))
            if revdb.current_time() != revdb.total_time():
                revdb.go_forward(1, went_fw, "zz")
        #
        def _nothing(arg):
            pass
        #
        def blip(cmdline):
            revdb.send_output('<<<' + cmdline + '>>>\n')
            if cmdline == 'oops':
                for i in range(1000):
                    print 42     # I/O not permitted
            if cmdline == 'raise-and-catch':
                try:
                    g(cmdline)
                except ValueError:
                    pass
            if cmdline == 'crash':
                raise ValueError
            if cmdline == 'get-value':
                revdb.send_output('%d,%d,%d\n' % (revdb.current_time(),
                                                  revdb.most_recent_fork(),
                                                  revdb.total_time()))
            if cmdline == 'go-fw':
                revdb.go_forward(1, went_fw, "xx")
            if cmdline == 'change-time':
                revdb.jump_in_time(2, changed_time, "xyzzy")
            if cmdline == 'set-break-after-0':
                dbstate.break_after = 0
            revdb.send_output('blipped\n')
        lambda_blip = lambda: blip
        #
        class DBState:
            break_after = -1
        dbstate = DBState()
        #
        def main(argv):
            revdb.register_debug_command('r', lambda_blip)
            for i, op in enumerate(argv[1:]):
                revdb.stop_point()
                if i == dbstate.break_after:
                    revdb.send_output('breakpoint!\n')
                    revdb.go_forward(1, _nothing, "")
                print op
            return 9
        compile(cls, main, [], backendopt=False)
        assert run(cls, 'abc d ef') == 'abc\nd\nef\n'

    def test_run_blip(self):
        child = self.replay()
        child.expectx('(3)$ ')
        child.sendline('r  foo  bar  baz  ')
        child.expectx('<<<foo  bar  baz>>>\r\n'
                      'blipped\r\n'
                      '(3)$ ')

    def test_io_not_permitted(self):
        child = self.replay()
        child.expectx('(3)$ ')
        child.sendline('r oops')
        child.expectx('<<<oops>>>\r\n')
        child.expectx(': Attempted to do I/O or access raw memory\r\n'
                      '(3)$ ')

    def test_interaction_with_forward(self):
        child = self.replay()
        child.expectx('(3)$ ')
        child.sendline('__go 1')
        child.expectx('(1)$ ')
        child.sendline('r oops')
        child.expectx('<<<oops>>>\r\n')
        child.expectx('Attempted to do I/O or access raw memory\r\n'
                      '(1)$ ')
        child.sendline('__forward 50')
        child.expectx('At end.\r\n'
                      '(3)$ ')

    def test_raise_and_catch(self):
        child = self.replay()
        child.expectx('(3)$ ')
        child.sendline('r raise-and-catch')
        child.expectx('<<<raise-and-catch>>>\r\n'
                      'blipped\r\n'
                      '(3)$ ')

    def test_crash(self):
        child = self.replay()
        child.expectx('(3)$ ')
        child.sendline('r crash')
        child.expectx('<<<crash>>>\r\n'
                      'Command crashed with ValueError\r\n'
                      '(3)$ ')

    def test_get_value(self):
        child = self.replay()
        child.expectx('(3)$ ')
        child.sendline('__go 2')
        child.expectx('(2)$ ')
        child.sendline('r get-value')
        child.expectx('<<<get-value>>>\r\n'
                      '2,1,3\r\n'
                      'blipped\r\n'
                      '(2)$ ')

    def test_go_fw(self):
        child = self.replay()
        child.expectx('(3)$ ')
        child.sendline('__go 1')
        child.expectx('(1)$ ')
        child.sendline('r go-fw')
        child.expectx('<<<go-fw>>>\r\n'
                      'blipped\r\n'
                      'went-fw xx -> 2\r\n'
                      'went-fw yy -> 3\r\n'
                      '(3)$ ')

    def test_change_time(self):
        child = self.replay()
        child.expectx('(3)$ ')
        child.sendline('r change-time')
        child.expectx('<<<change-time>>>\r\n'
                      'changed-time xyzzy -> 2\r\n'
                      'went-fw zz -> 3\r\n'
                      '(3)$ ')

    def test_dynamic_breakpoint(self):
        child = self.replay()
        child.expectx('(3)$ ')
        child.sendline('__go 1')
        child.expectx('(1)$ ')
        child.sendline('r set-break-after-0')
        child.expectx('(1)$ ')
        child.sendline('__forward 5')
        child.expectx('breakpoint!\r\n'
                      '(2)$ ')
