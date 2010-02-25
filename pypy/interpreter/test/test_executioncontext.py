import py
from pypy.interpreter import executioncontext
from pypy.conftest import gettestobjspace, option

class Finished(Exception):
    pass


class TestExecutionContext:

    def test_action(self):

        class DemoAction(executioncontext.AsyncAction):
            counter = 0
            def perform(self, ec, frame):
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
            def perform(self, ec, frame):
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
        l = []
        
        def profile_func(space, w_arg, frame, event, w_aarg):
            assert w_arg is space.w_None
            l.append(event)
        
        space = self.space
        space.getexecutioncontext().setllprofile(profile_func, space.w_None)
        space.appexec([], """():
        pass
        """)
        space.getexecutioncontext().setllprofile(None, None)
        assert l == ['call', 'return', 'call', 'return']

    def test_llprofile_c_call(self):
        l = []
        
        def profile_func(space, w_arg, frame, event, w_aarg):
            assert w_arg is space.w_None
            l.append(event)

        space = self.space
        space.getexecutioncontext().setllprofile(profile_func, space.w_None)

        def check_snippet(snippet):
            space.appexec([], """():
            %s
            return
            """ % snippet)
            space.getexecutioncontext().setllprofile(None, None)
            assert l == ['call', 'return', 'call', 'c_call', 'c_return', 'return']

        check_snippet('l = []; l.append(42)')
        check_snippet('max(1, 2)')
        check_snippet('args = (1, 2); max(*args)')
        check_snippet('max(1, 2, **{})')
        check_snippet('args = (1, 2); max(*args, **{})')
        check_snippet('abs(val=0)')
        
    def test_llprofile_c_exception(self):
        l = []
        
        def profile_func(space, w_arg, frame, event, w_aarg):
            assert w_arg is space.w_None
            l.append(event)

        space = self.space
        space.getexecutioncontext().setllprofile(profile_func, space.w_None)

        def check_snippet(snippet):
            space.appexec([], """():
            try:
                %s
            except:
                pass
            return
            """ % snippet)
            space.getexecutioncontext().setllprofile(None, None)
            assert l == ['call', 'return', 'call', 'c_call', 'c_exception', 'return']

        check_snippet('d = {}; d.__getitem__(42)')

    def test_c_call_setprofile_outer_frame(self):
        space = self.space
        w_events = space.appexec([], """():
        import sys
        l = []
        def profile(frame, event, arg):
            l.append(event)

        def foo():
            sys.setprofile(profile)

        def bar():
            foo()
            max(1, 2)

        bar()
        sys.setprofile(None)
        return l
        """)
        events = space.unwrap(w_events)
        assert events == ['return', 'c_call', 'c_return', 'return', 'c_call']

    def test_c_call_setprofile_strange_method(self):
        space = self.space
        w_events = space.appexec([], """():
        import sys
        class A(object):
            def __init__(self, value):
                self.value = value
            def meth(self):
                pass
        MethodType = type(A.meth)
        strangemeth = MethodType(A, 42, int)
        l = []
        def profile(frame, event, arg):
            l.append(event)

        def foo():
            sys.setprofile(profile)

        def bar():
            foo()
            strangemeth()

        bar()
        sys.setprofile(None)
        return l
        """)
        events = space.unwrap(w_events)
        assert events == ['return', 'call', 'return', 'return', 'c_call']

    def test_c_call_profiles_immediately(self):
        space = self.space
        w_events = space.appexec([], """():
        import sys
        l = []
        def profile(frame, event, arg):
            l.append((event, arg))

        def bar():
            sys.setprofile(profile)
            max(3, 4)

        bar()
        sys.setprofile(None)
        return l
        """)
        events = space.unwrap(w_events)
        assert [i[0] for i in events] == ['c_call', 'c_return', 'return', 'c_call']
        assert events[0][1] == events[1][1]

    def test_tracing_range_builtinshortcut(self):
        opts = {"objspace.opcodes.CALL_LIKELY_BUILTIN": True}
        space = gettestobjspace(**opts)
        source = """def f(profile):
        import sys
        sys.setprofile(profile)
        range(10)
        sys.setprofile(None)
        """
        w_events = space.appexec([space.wrap(source)], """(source):
        import sys
        l = []
        def profile(frame, event, arg):
            l.append((event, arg))
        d = {}
        exec source in d
        f = d['f']
        f(profile)
        import dis
        print dis.dis(f)
        return l
        """)
        events = space.unwrap(w_events)
        assert [i[0] for i in events] == ['c_call', 'c_return', 'c_call']

    def test_profile_and_exception(self):
        space = self.space
        w_res = space.appexec([], """():
        l = []
        
        def profile(*args):
            l.append(sys.exc_info()[0])

        import sys
        try:
            sys.setprofile(profile)
            try:
                x
            except:
                expected = sys.exc_info()[0]
                assert expected is NameError
                for i in l:
                    assert expected is l[0]
        finally:
            sys.setprofile(None)
        """)


class AppTestDelNotBlocked:

    def setup_method(self, meth):
        if not option.runappdirect:
            py.test.skip("test is meant for running with py.test -A")
        from pypy.tool.udir import udir
        tmpfile = udir.join('test_execution_context')
        tmpfile.write("""
import gc
class X(object):
    def __del__(self):
        print "Called", self.num
def f():
    x1 = X(); x1.num = 1
    x2 = X(); x2.num = 2
    x1.next = x2
f()
gc.collect()
gc.collect()
""")
        self.tmpfile = str(tmpfile)
        self.w_tmpfile = self.space.wrap(self.tmpfile)

    def test_del_not_blocked(self):
        # test the behavior fixed in r71420: before, only one __del__
        # would be called
        import os, sys
        print sys.executable, self.tmpfile
        g = os.popen('"%s" "%s"' % (sys.executable, self.tmpfile), 'r')
        data = g.read()
        g.close()
        assert 'Called 1' in data
        assert 'Called 2' in data
