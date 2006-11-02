import py
from pypy.interpreter import miscutils


class TestExecutionContext:

    def test_action(self):
        class Finished(Exception):
            pass

        class DemoAction(miscutils.Action):
            def __init__(self, repeat):
                self.repeat = repeat
                self.counter = 0
            def perform(self):
                self.counter += 1
                if self.counter == 10:
                    raise Finished

        a1 = DemoAction(False)
        a2 = DemoAction(True)
        a3 = DemoAction(False)

        space = self.space
        space.pending_actions.append(a1)
        space.getexecutioncontext().add_pending_action(a2)
        space.getexecutioncontext().add_pending_action(a3)

        py.test.raises(Finished, space.appexec, [], """():
            n = 50000
            while n > 0:
                n -= 1
        """)
        assert a1.counter == 1
        assert a2.counter == 10
        assert a3.counter == 1
