import py
import os, sys, subprocess
import re, array, struct
from rpython.tool.udir import udir
from rpython.translator.interactive import Translation
from rpython.rlib.rarithmetic import LONG_BIT
from rpython.rlib import objectmodel, revdb
from rpython.rlib.rarithmetic import intmask
from rpython.rtyper.annlowlevel import cast_gcref_to_instance
from rpython.rtyper.lltypesystem import lltype, llmemory

from rpython.translator.revdb.revmsg import *


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


def compile(self, entry_point, argtypes, backendopt=True,
            withsmallfuncsets=None):
    t = Translation(entry_point, None, gc="boehm")
    self.t = t
    t.config.translation.reverse_debugger = True
    t.config.translation.rweakref = False
    t.config.translation.lldebug0 = True
    if withsmallfuncsets is not None:
        t.config.translation.withsmallfuncsets = withsmallfuncsets
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

    @py.test.mark.parametrize('limit', [3, 5])
    def test_dont_record_small_funcset_conversions(self, limit):
        def f1():
            return 111
        def f2():
            return 222
        def f3():
            return 333
        def g(n):
            if n & 1:
                return f1
            else:
                return f2
        def main(argv):
            x = g(len(argv))    # can be f1 or f2
            if len(argv) > 5:
                x = f3  # now can be f1 or f2 or f3
            print x()
            return 9
        self.compile(main, [], backendopt=False, withsmallfuncsets=limit)
        for input, expected_output in [
                ('2 3', '111\n'),
                ('2 3 4', '222\n'),
                ('2 3 4 5 6 7', '333\n'),
                ]:
            out = self.run(input)
            assert out == expected_output
            rdb = self.fetch_rdb([self.exename] + input.split())
            # write() call
            x = rdb.next(); assert x == len(out)
            x = rdb.next('i'); assert x == 0      # errno
            x = rdb.next('q'); assert x == 0      # number of stop points
            assert rdb.done()


class InteractiveTests(object):

    def replay(self):
        subproc = subprocess.Popen(
            [str(self.exename), '--revdb-replay', str(self.rdbname)],
            stdin  = subprocess.PIPE,
            stdout = subprocess.PIPE)
        self.subproc = subproc
        return ReplayProcess(subproc.stdin, subproc.stdout)


class TestSimpleInterpreter(InteractiveTests):

    def setup_class(cls):
        def main(argv):
            lst = [argv[0], 'prebuilt']
            for op in argv[1:]:
                revdb.stop_point()
                print op
                lst.append(op + '??')   # create a new string here
            for x in lst:
                print revdb.get_unique_id(x)
            return 9
        compile(cls, main, [], backendopt=False)
        assert run(cls, 'abc d ef') == ('abc\nd\nef\n'
                                        '3\n0\n12\n15\n17\n')
        rdb = fetch_rdb(cls, [cls.exename, 'abc', 'd', 'ef'])
        assert rdb.number_of_stop_points() == 3

    def test_go(self):
        child = self.replay()
        child.expect(ANSWER_INIT, INIT_VERSION_NUMBER, 3)
        child.expect(ANSWER_STD, 1, Ellipsis)
        child.send(Message(CMD_FORWARD, 2))
        child.expect(ANSWER_STD, 3, Ellipsis)
        child.send(Message(CMD_FORWARD, 2))
        child.expect(ANSWER_AT_END)

    def test_quit(self):
        child = self.replay()
        child.expect(ANSWER_INIT, INIT_VERSION_NUMBER, 3)
        child.expect(ANSWER_STD, 1, Ellipsis)
        child.send(Message(CMD_QUIT))
        assert self.subproc.wait() == 0


class TestDebugCommands(InteractiveTests):

    def setup_class(cls):
        #
        class Stuff:
            pass
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
        def callback_track_obj(gcref):
            revdb.send_output("callback_track_obj\n")
            dbstate.gcref = gcref
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
            if cmdline == 'change-time-non-exact':
                revdb.jump_in_time(2, changed_time, "nonx", exact=False)
            if cmdline == 'set-break-after-0':
                dbstate.break_after = 0
            if cmdline == 'print-id':
                revdb.send_output('obj.x=%d %d %d\n' % (
                    dbstate.stuff.x,
                    revdb.get_unique_id(dbstate.stuff),
                    revdb.currently_created_objects()))
            if cmdline.startswith('track-object '):
                uid = int(cmdline[len('track-object '):])
                dbstate.gcref = lltype.nullptr(llmemory.GCREF.TO)
                revdb.track_object(uid, callback_track_obj)
            if cmdline == 'get-tracked-object':
                if dbstate.gcref:
                    revdb.send_output('got obj.x=%d\n' % (
                        cast_gcref_to_instance(Stuff, dbstate.gcref).x,))
                else:
                    revdb.send_output('none\n')
            if cmdline == 'first-created-uid':
                revdb.send_output('first-created-uid=%d\n' % (
                    revdb.first_created_object_uid(),))
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
                dbstate.stuff = Stuff()
                dbstate.stuff.x = i + 1000
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

    def test_change_time_non_exact(self):
        child = self.replay()
        child.expectx('(3)$ ')
        child.sendline('r change-time-non-exact')
        child.expectx('<<<change-time-non-exact>>>\r\n'
                      'changed-time nonx -> 1\r\n'
                      'went-fw zz -> 2\r\n'
                      'went-fw yy -> 3\r\n'
                      '(3)$ ')

    def test_dynamic_breakpoint(self):
        py.test.skip("unsure if that's needed")
        child = self.replay()
        child.expectx('(3)$ ')
        child.sendline('__go 1')
        child.expectx('(1)$ ')
        child.sendline('r set-break-after-0')
        child.expectx('(1)$ ')
        child.sendline('__forward 5')
        child.expectx('breakpoint!\r\n'
                      '(2)$ ')

    def test_get_unique_id_and_track_object(self):
        child = self.replay()
        child.expectx('(3)$ ')
        child.sendline('r print-id')
        child.expect(re.escape('<<<print-id>>>\r\n')
                     + r'obj.x=1002 (\d+) (\d+)'
                     + re.escape('\r\n'
                                 'blipped\r\n'
                                 '(3)$ '))
        object_id_3rd = int(child.match.group(1))
        created_objects_3rd = int(child.match.group(2))
        assert 0 < object_id_3rd < created_objects_3rd
        #
        child.sendline('__go 1')
        child.expectx('(1)$ ')
        child.sendline('r print-id')
        child.expect(re.escape('<<<print-id>>>\r\n')
                     + r'obj.x=1000 (\d+) (\d+)'
                     + re.escape('\r\n'
                                 'blipped\r\n'
                                 '(1)$ '))
        object_id_1st = int(child.match.group(1))
        created_objects_1st = int(child.match.group(2))
        assert 0 < object_id_1st < created_objects_1st
        assert created_objects_1st <= object_id_3rd   # only created afterwards
        #
        child.sendline('r track-object %d' % object_id_3rd)
        child.expectx('<<<track-object %d>>>\r\n' % object_id_3rd +
                      'blipped\r\n'
                      '(1)$ ')
        for i in [1, 2]:
            child.sendline('r get-tracked-object')
            child.expectx('<<<get-tracked-object>>>\r\n'
                          'none\r\n'
                          'blipped\r\n'
                          '(%d)$ ' % i)
            child.sendline('__forward 1')
            child.expectx('(%d)$ ' % (i + 1))
        child.sendline('r get-tracked-object')
        child.expectx('<<<get-tracked-object>>>\r\n'
                      'got obj.x=1002\r\n'
                      'blipped\r\n'
                      '(3)$ ')
        child.sendline('__go 3')
        child.expectx('(3)$ ')
        child.sendline('r get-tracked-object')
        child.expectx('<<<get-tracked-object>>>\r\n'
                      'none\r\n'
                      'blipped\r\n'
                      '(3)$ ')
        #
        child.sendline('__go 2')
        child.expectx('(2)$ ')
        child.sendline('r print-id')
        child.expect(re.escape('<<<print-id>>>\r\n')
                     + r'obj.x=1001 (\d+) (\d+)'
                     + re.escape('\r\n'
                                 'blipped\r\n'
                                 '(2)$ '))
        object_id_2nd = int(child.match.group(1))
        created_objects_2nd = int(child.match.group(2))
        #
        child.sendline('r track-object %d' % object_id_2nd)
        child.expectx('<<<track-object %d>>>\r\n' % object_id_2nd +
                    'cannot track the creation of an object already created\r\n'
                      'blipped\r\n'
                      '(2)$ ')
        child.sendline('r track-object 0')
        child.expectx('<<<track-object 0>>>\r\n'
                      'cannot track a prebuilt or debugger-created object\r\n'
                      'blipped\r\n'
                      '(2)$ ')
        child.sendline('__go 1')
        child.expectx('(1)$ ')
        child.sendline('r track-object %d' % object_id_2nd)
        child.expectx('<<<track-object %d>>>\r\n' % object_id_2nd +
                      'blipped\r\n'
                      '(1)$ ')
        child.sendline('__forward 2')
        child.expectx('(3)$ ')
        child.sendline('r get-tracked-object')
        child.expectx('<<<get-tracked-object>>>\r\n'
                      'got obj.x=1001\r\n'
                      'blipped\r\n'
                      '(3)$ ')
        child.sendline('__forward 1')
        child.expectx('At end.\r\n'
                      '(3)$ ')
        child.sendline('r get-tracked-object')
        child.expectx('<<<get-tracked-object>>>\r\n'
                      'none\r\n'
                      'blipped\r\n'
                      '(3)$ ')

    def test_first_created_uid(self):
        child = self.replay()
        child.expectx('(3)$ ')
        child.sendline('r first-created-uid')
        child.expectx('<<<first-created-uid>>>\r\n')
        child.expect('first-created-uid=(\d+)\r\n')
        first_created_id = int(child.match.group(1))
        child.expectx('blipped\r\n'
                      '(3)$ ')
        child.sendline('__go 1')
        child.expectx('(1)$ ')
        child.sendline('r print-id')
        child.expect(re.escape('<<<print-id>>>\r\n')
                     + r'obj.x=1000 (\d+) (\d+)'
                     + re.escape('\r\n'
                                 'blipped\r\n'
                                 '(1)$ '))
        assert int(child.match.group(2)) == first_created_id
