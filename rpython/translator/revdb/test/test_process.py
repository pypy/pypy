import py
from rpython.rlib import revdb
from rpython.rlib.debug import debug_print
from rpython.translator.revdb.message import *
from rpython.translator.revdb.process import ReplayProcessGroup, Breakpoint

from hypothesis import given, strategies


class TestReplayProcessGroup:

    def setup_class(cls):
        from rpython.translator.revdb.test.test_basic import compile, run

        class Stuff:
            pass

        class DBState:
            break_loop = -2
        dbstate = DBState()

        def blip(cmd, extra):
            debug_print('<<<', cmd.c_cmd, cmd.c_arg1,
                               cmd.c_arg2, cmd.c_arg3, extra, '>>>')
            if extra == 'set-breakpoint':
                dbstate.break_loop = cmd.c_arg1
            revdb.send_answer(42, cmd.c_cmd, -43, -44, extra)
        lambda_blip = lambda: blip

        def main(argv):
            revdb.register_debug_command(100, lambda_blip)
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
