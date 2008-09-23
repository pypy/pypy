import py
from pypy.interpreter import executioncontext


class Finished(Exception):
    pass


class TestExecutionContext:

    def test_action(self):

        class DemoAction(executioncontext.AsyncAction):
            counter = 0
            def perform(self, ec):
                self.counter += 1
                if self.counter == 10:
                    raise Finished

        space = self.space
        a1 = DemoAction(space)
        space.actionflag.register_action(a1)
        for i in range(20):
            # assert does not raise:
            space.appexec([], """():
                n = 5
                return n + 2
            """)
        try:
            for i in range(20):
                a1.fire()
                space.appexec([], """():
                    n = 5
                    return n + 2
                """)
                assert a1.counter == i + 1
        except Finished:
            pass
        assert i == 9

    def test_periodic_action(self):

        class DemoAction(executioncontext.PeriodicAsyncAction):
            counter = 0
            def perform(self, ec):
                self.counter += 1
                print '->', self.counter
                if self.counter == 3:
                    raise Finished

        space = self.space
        a2 = DemoAction(space)
        space.actionflag.register_action(a2)
        try:
            for i in range(500):
                space.appexec([], """():
                    n = 5
                    return n + 2
                """)
        except Finished:
            pass
        assert space.sys.checkinterval / 10 < i < space.sys.checkinterval * 3

    def test_llprofile(self):
        py.test.skip("not working yet")
        l = []
        
        def profile_func(space, w_arg, frame, event, w_aarg):
            assert w_arg is space.w_None
            l.append(event)
        
        space = self.space
        space.getexecutioncontext().setllprofile(profile_func, space.w_None)
        space.appexec([], """():
        l = []
        l.append(3)
        """)
        space.getexecutioncontext().setllprofile(None, None)
        assert l == ['call', 'return', 'call', 'c_call', 'c_return', 'return']

