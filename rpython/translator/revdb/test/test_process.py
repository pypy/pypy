import py, sys
from cStringIO import StringIO
from rpython.rlib import revdb
from rpython.rlib.debug import debug_print, ll_assert
from rpython.rtyper.annlowlevel import cast_gcref_to_instance
from rpython.translator.revdb.message import *
from rpython.translator.revdb.process import ReplayProcessGroup, Breakpoint

from hypothesis import given, strategies


class stdout_capture(object):
    def __enter__(self):
        self.old_stdout = sys.stdout
        sys.stdout = self.buffer = StringIO()
        return self.buffer
    def __exit__(self, *args):
        sys.stdout = self.old_stdout


class TestReplayProcessGroup:

    def setup_class(cls):
        from rpython.translator.revdb.test.test_basic import compile, run

        class Stuff:
            pass

        class DBState:
            break_loop = -2
            stuff = None
            metavar = None
            printed_stuff = None
            watch_future = -1
        dbstate = DBState()

        def blip(cmd, extra):
            debug_print('<<<', cmd.c_cmd, cmd.c_arg1,
                               cmd.c_arg2, cmd.c_arg3, extra, '>>>')
            if extra == 'set-breakpoint':
                dbstate.break_loop = cmd.c_arg1
            revdb.send_answer(42, cmd.c_cmd, -43, -44, extra)
        lambda_blip = lambda: blip

        def command_print(cmd, extra):
            if extra == 'print-me':
                stuff = dbstate.stuff
            elif extra == '$0':
                stuff = dbstate.metavar
            else:
                assert False
            uid = revdb.get_unique_id(stuff)
            ll_assert(uid > 0, "uid == 0")
            revdb.send_nextnid(uid)   # outputs '$NUM = '
            revdb.send_output('stuff\n')
            dbstate.printed_stuff = stuff
        lambda_print = lambda: command_print

        def command_attachid(cmd, extra):
            index_metavar = cmd.c_arg1
            uid = cmd.c_arg2
            ll_assert(index_metavar == 0, "index_metavar != 0")  # in this test
            dbstate.metavar = dbstate.printed_stuff
            if dbstate.metavar is None:
                # uid not found, probably a future object
                dbstate.watch_future = uid
        lambda_attachid = lambda: command_attachid

        def command_allocating(uid, gcref):
            stuff = cast_gcref_to_instance(Stuff, gcref)
            # 'stuff' is just allocated; 'stuff.x' is not yet initialized
            dbstate.printed_stuff = stuff
            if dbstate.watch_future != -1:
                ll_assert(dbstate.watch_future == uid,
                          "watch_future out of sync")
                dbstate.watch_future = -1
                dbstate.metavar = stuff
        lambda_allocating = lambda: command_allocating

        def main(argv):
            revdb.register_debug_command(100, lambda_blip)
            revdb.register_debug_command(CMD_PRINT, lambda_print)
            revdb.register_debug_command(CMD_ATTACHID, lambda_attachid)
            revdb.register_debug_command("ALLOCATING", lambda_allocating)
            for i, op in enumerate(argv[1:]):
                dbstate.stuff = Stuff()
                dbstate.stuff.x = i + 1000
                if i == dbstate.break_loop or i == dbstate.break_loop + 1:
                    revdb.breakpoint(99)
                revdb.stop_point()
                print op
            return 9
        compile(cls, main, backendopt=False)
        assert run(cls, 'abc d ef g h i j k l m') == (
            'abc\nd\nef\ng\nh\ni\nj\nk\nl\nm\n')


    def test_init(self):
        group = ReplayProcessGroup(str(self.exename), self.rdbname)
        assert group.get_max_time() == 10
        assert group.get_next_clone_time() == 4

    def test_forward(self):
        group = ReplayProcessGroup(str(self.exename), self.rdbname)
        group.go_forward(100)
        assert group.get_current_time() == 10
        assert sorted(group.paused) == [1, 4, 6, 8, 9, 10]
        assert group._check_current_time(10)

    @given(strategies.lists(strategies.integers(min_value=1, max_value=10)))
    def test_jump_in_time(self, target_times):
        group = ReplayProcessGroup(str(self.exename), self.rdbname)
        for target_time in target_times:
            group.jump_in_time(target_time)
            group._check_current_time(target_time)

    def test_breakpoint_b(self):
        group = ReplayProcessGroup(str(self.exename), self.rdbname)
        group.active.send(Message(100, 6, extra='set-breakpoint'))
        group.active.expect(42, 100, -43, -44, 'set-breakpoint')
        group.active.expect(ANSWER_READY, 1, Ellipsis)
        e = py.test.raises(Breakpoint, group.go_forward, 10, 'b')
        assert e.value.time == 7
        assert e.value.nums == [99]
        group._check_current_time(7)

    def test_breakpoint_r(self):
        group = ReplayProcessGroup(str(self.exename), self.rdbname)
        group.active.send(Message(100, 6, extra='set-breakpoint'))
        group.active.expect(42, 100, -43, -44, 'set-breakpoint')
        group.active.expect(ANSWER_READY, 1, Ellipsis)
        e = py.test.raises(Breakpoint, group.go_forward, 10, 'r')
        assert e.value.time == 7
        assert e.value.nums == [99]
        group._check_current_time(10)

    def test_breakpoint_i(self):
        group = ReplayProcessGroup(str(self.exename), self.rdbname)
        group.active.send(Message(100, 6, extra='set-breakpoint'))
        group.active.expect(42, 100, -43, -44, 'set-breakpoint')
        group.active.expect(ANSWER_READY, 1, Ellipsis)
        group.go_forward(10, 'i')    # does not raise Breakpoint

    def test_print_cmd(self):
        group = ReplayProcessGroup(str(self.exename), self.rdbname)
        group.go_forward(1)
        assert group.get_current_time() == 2
        with stdout_capture() as buf:
            group.print_cmd('print-me')
        assert buf.getvalue() == "$0 = stuff\n"
        return group

    def test_print_metavar(self):
        group = self.test_print_cmd()
        with stdout_capture() as buf:
            group.print_cmd('$0', nids=[0])
        assert buf.getvalue() == "$0 = stuff\n"

    def test_jump_and_print_metavar(self):
        group = self.test_print_cmd()
        assert group.is_tainted()
        group.jump_in_time(2)
        with stdout_capture() as buf:
            group.print_cmd('$0', nids=[0])
        assert buf.getvalue() == "$0 = stuff\n"
