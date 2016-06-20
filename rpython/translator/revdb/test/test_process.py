from rpython.rlib import revdb
from rpython.translator.revdb.message import *
from rpython.translator.revdb.process import ReplayProcessGroup

from hypothesis import given, strategies


class TestReplayProcessGroup:

    def setup_class(cls):
        from rpython.translator.revdb.test.test_basic import compile, run

        class Stuff:
            pass

        class DBState:
            pass
        dbstate = DBState()

        def main(argv):
            for i, op in enumerate(argv[1:]):
                dbstate.stuff = Stuff()
                dbstate.stuff.x = i + 1000
                revdb.stop_point()
                print op
            return 9
        compile(cls, main, [], backendopt=False)
        assert run(cls, 'abc d ef g h i j k l m') == (
            'abc\nd\nef\ng\nh\ni\nj\nk\nl\nm\n')


    def test_init(self):
        group = ReplayProcessGroup(str(self.exename), self.rdbname)
        assert group.get_max_time() == 10
        assert group.get_next_clone_time() == 4

    def test_forward(self):
        group = ReplayProcessGroup(str(self.exename), self.rdbname)
        group.forward(100)
        assert group.get_current_time() == 10
        assert sorted(group.paused) == [1, 4, 6, 8, 9, 10]
        assert group._check_current_time(10)

    @given(strategies.lists(strategies.integers(min_value=1, max_value=10)))
    def test_jump_in_time(self, target_times):
        group = ReplayProcessGroup(str(self.exename), self.rdbname)
        for target_time in target_times:
            group.jump_in_time(target_time)
            group._check_current_time(target_time)
