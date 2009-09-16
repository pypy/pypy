import py
from pypy.interpreter import executioncontext
from pypy.interpreter.executioncontext import ExecutionContext
from pypy.conftest import gettestobjspace

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



class TestFrameChaining(object):
    class EC(ExecutionContext):
        _some_frame = None
        def __init__(self, jitted=False):
            self.jitted = jitted
            self.virtualizable = None
            self.framestackdepth = 0
            self._init_frame_chain()

        def _we_are_jitted(self):
            return self.jitted

        def _get_some_frame(self):
            if self._some_frame:
                self._some_frame.look_at()
            return self._some_frame
        def _set_some_frame(self, frame):
            if frame is not None:
                frame.force()
            self._some_frame = frame
        some_frame = property(_get_some_frame, _set_some_frame)

    class Frame(object):
        _f_back_some = None
        _f_forward = None

        def __init__(self, ec, virtual_with_base_frame=None):
            self.ec = ec
            self.virtual_with_base_frame = virtual_with_base_frame
            self.escaped = not virtual_with_base_frame
            ExecutionContext._init_chaining_attributes(self)

        def f_back(self):
            return ExecutionContext._extract_back_from_frame(self)

        def force_f_back(self):
            return ExecutionContext._force_back_of_frame(self)

        def force(self):
            if not self.escaped:
                self.virtual_with_base_frame = None
                self.escaped = True
                if self._f_back_some:
                    self._f_back_some.force()
                if self._f_forward:
                    self._f_back_some.force()

        def look_at(self):
            if (not self.ec.jitted or
                self.ec.virtualizable is not self.virtual_with_base_frame):
                self.force()

        def store_ref_to(self, other):
            if (other.virtual_with_base_frame is not self and
                other.virtual_with_base_frame is not self.virtual_with_base_frame):
                other.force()

        def _get_f_back_some(self):
            self.look_at()
            return self._f_back_some
        def _set_f_back_some(self, frame):
            self.look_at()
            if frame:
                frame.look_at()
                self.store_ref_to(frame)
            self._f_back_some = frame
        f_back_some = property(_get_f_back_some, _set_f_back_some)
        
        def _get_f_forward(self):
            self.look_at()
            return self._f_forward
        def _set_f_forward(self, frame):
            self.look_at()
            if frame:
                frame.look_at()
                self.store_ref_to(frame)
            self._f_forward = frame
        f_forward = property(_get_f_forward, _set_f_forward)

    def test_f_back_no_jit(self):
        ec = self.EC()
        frame = self.Frame(ec)
        frame2 = self.Frame(ec)
        frame2.f_back_some = frame

        frame3 = self.Frame(ec)
        frame3.f_back_some = frame2

        assert frame3.f_back() is frame2
        assert frame2.f_back() is frame
        assert frame.f_back() is None

    def test_f_back_jit(self):
        ec = self.EC()
        frame = self.Frame(ec) # real frame
        frame2 = self.Frame(ec) # virtual frame
        frame2.f_back_some = frame
        frame.f_forward = frame2

        frame3 = self.Frame(ec) # virtual frame
        frame3.f_back_some = frame
        frame2.f_forward = frame3

        assert frame3.f_back() is frame2
        assert frame2.f_back() is frame
        assert frame.f_back() is None

        frame4 = self.Frame(ec) # real frame again
        frame4.f_back_some = frame
        assert frame4.f_back() is frame3

    def test_gettopframe_no_jit(self):
        ec = self.EC()
        frame = self.Frame(ec)
        ec.some_frame = frame
        assert ec.gettopframe() is frame

    def test_gettopframe_jit(self):
        ec = self.EC()
        frame = self.Frame(ec) # real frame
        ec.some_frame = frame
        assert ec.gettopframe() is frame

        frame2 = self.Frame(ec) # virtual frame
        frame2.f_back_some = frame
        frame.f_forward = frame2
        assert ec.gettopframe() is frame2

        frame3 = self.Frame(ec) # virtual frame
        frame3.f_back_some = frame
        frame2.f_forward = frame3
        assert ec.gettopframe() is frame3

        frame4 = self.Frame(ec) # real frame again
        frame4.f_back_some = frame
        ec.some_frame = frame4
        assert ec.gettopframe() is frame4

    def test_frame_chain(self):

        ec = self.EC()

        assert ec.some_frame is None
        assert ec.framestackdepth == 0

        frame = self.Frame(ec)
        ec._chain(frame)
        assert ec.some_frame is frame
        assert ec.framestackdepth == 1
        assert frame.f_back_some is None
        assert frame.f_forward is None
        assert ec.gettopframe() is frame
        assert ec._extract_back_from_frame(frame) is None
        
        frame2 = self.Frame(ec)
        ec._chain(frame2)
        assert ec.some_frame is frame2
        assert ec.framestackdepth == 2
        assert frame2.f_back_some is frame
        assert frame.f_forward is None
        assert frame2.f_forward is None
        assert ec.gettopframe() is frame2
        assert ec._extract_back_from_frame(frame2) is frame
        assert ec._extract_back_from_frame(frame) is None
       
        frame3 = self.Frame(ec)
        ec._chain(frame3)
        assert ec.some_frame is frame3
        assert frame3.f_back_some is frame2
        assert frame2.f_forward is None
        assert ec.gettopframe() is frame3
        assert ec._extract_back_from_frame(frame3) is frame2
        assert ec._extract_back_from_frame(frame2) is frame
        assert ec._extract_back_from_frame(frame) is None

        assert frame3.f_back() is frame2
        ec._unchain(frame3)
        assert ec.some_frame is frame2
        assert ec.framestackdepth == 2
        assert frame2.f_forward is None
        assert frame3.f_back_some is frame2
        assert ec.gettopframe() is frame2
        assert ec._extract_back_from_frame(frame2) is frame
        assert ec._extract_back_from_frame(frame) is None
        
        assert frame2.f_back() is frame
        ec._unchain(frame2)
        assert ec.some_frame is frame
        assert ec.framestackdepth == 1
        assert frame.f_forward is None
        assert frame2.f_back_some is frame
        assert ec.gettopframe() is frame
        assert ec._extract_back_from_frame(frame) is None

        assert frame.f_back() is None
        ec._unchain(frame)
        assert ec.some_frame is None
        assert ec.framestackdepth == 0
        assert frame.f_back_some is None
        assert ec.gettopframe() is None

    def test_frame_chain_forced(self):

        ec = self.EC()

        frame = self.Frame(ec)
        ec._chain(frame)
        assert ec.gettopframe() is frame
        assert ec._extract_back_from_frame(frame) is None
        
        frame2 = self.Frame(ec)
        ec._chain(frame2)
        assert ec.some_frame is frame2
        assert ec.framestackdepth == 2
        assert frame2.f_back_some is frame
        assert frame.f_forward is None
        assert frame2.f_forward is None
        res = frame2.force_f_back()
        assert res is frame
        assert frame.f_back_forced
        assert ec.gettopframe() is frame2
        assert ec._extract_back_from_frame(frame2) is frame
        assert ec._extract_back_from_frame(frame) is None
        
        frame3 = self.Frame(ec)
        ec._chain(frame3)
        assert ec.gettopframe() is frame3
        assert ec._extract_back_from_frame(frame3) is frame2
        assert ec._extract_back_from_frame(frame2) is frame
        assert ec._extract_back_from_frame(frame) is None

        assert frame3.f_back() is frame2
        ec._unchain(frame3)
        assert ec.some_frame is frame2
        assert frame3.f_back_some is frame2
        assert ec.gettopframe() is frame2
        assert ec._extract_back_from_frame(frame2) is frame
        assert ec._extract_back_from_frame(frame) is None
        
        assert frame2.f_back() is frame
        ec._unchain(frame2)
        assert frame2.f_back_some is frame
        assert ec.gettopframe() is frame
        assert ec._extract_back_from_frame(frame) is None

        assert frame.f_back() is None
        ec._unchain(frame)
        assert ec.some_frame is None
        assert frame.f_back_some is None

        assert frame2.f_back() is frame
        assert frame.f_back() is None
        assert ec.gettopframe() is None


    def test_frame_chain_jitted(self):

        ec = self.EC()

        assert ec.some_frame is None
        assert ec.framestackdepth == 0
        assert ec.gettopframe() is None

        frame = self.Frame(ec)
        ec._chain(frame)
        assert ec.some_frame is frame
        assert ec.framestackdepth == 1
        assert frame.f_back_some is None
        assert frame.f_forward is None
        assert ec.gettopframe() is frame
        assert ec._extract_back_from_frame(frame) is None
        
        ec.jitted = True
        ec.virtualizable = frame
        frame2 = self.Frame(ec, frame)
        ec._chain(frame2)
        assert ec.some_frame is frame
        assert ec.framestackdepth == 2
        assert frame2.f_back_some is frame
        assert frame.f_forward is frame2
        assert frame2.f_forward is None
        assert ec.gettopframe() is frame2
        assert ec._extract_back_from_frame(frame2) is frame
        assert ec._extract_back_from_frame(frame) is None

        # recursive enter/leave seen by the jit
        frame3 = self.Frame(ec, frame)
        ec._chain(frame3)
        assert ec.some_frame is frame
        assert frame3.f_back_some is frame
        assert frame2.f_forward is frame3
        assert ec.gettopframe() is frame3
        assert ec._extract_back_from_frame(frame3) is frame2
        assert ec._extract_back_from_frame(frame2) is frame
        assert ec._extract_back_from_frame(frame) is None

        assert frame3.f_back() is frame2
        ec._unchain(frame3)
        assert ec.some_frame is frame
        assert ec.framestackdepth == 2
        assert frame2.f_forward is None
        assert frame3.f_back_some is frame
        assert not frame3.escaped
        assert not frame2.escaped
        assert ec.gettopframe() is frame2
        assert ec._extract_back_from_frame(frame2) is frame
        assert ec._extract_back_from_frame(frame) is None
       
        # recursive enter/leave not seen by the jit
        ec.jitted = False
        ec.virtualizable = None
        ec._chain(frame3)
        assert not frame2.escaped
        assert ec.some_frame is frame3
        assert frame3.f_back_some is frame
        assert frame2.f_forward is None
        assert frame3.escaped
        assert ec.gettopframe() is frame3
        assert ec._extract_back_from_frame(frame3) is frame2
        assert ec._extract_back_from_frame(frame2) is frame
        assert ec._extract_back_from_frame(frame) is None

        assert frame3.f_back() is frame2
        ec._unchain(frame3)
        assert ec.some_frame is frame
        assert ec.framestackdepth == 2
        assert frame2.f_forward is None
        assert frame3.f_back_some is frame
        assert ec.gettopframe() is frame2
        assert ec._extract_back_from_frame(frame2) is frame
        assert ec._extract_back_from_frame(frame) is None

        ec.jitted = True
        ec.virtualizable = frame

        assert frame2.f_back() is frame
        ec._unchain(frame2)
        assert ec.some_frame is frame
        assert ec.framestackdepth == 1
        assert frame.f_forward is None
        assert frame2.f_back_some is frame
        assert ec.gettopframe() is frame
        assert ec._extract_back_from_frame(frame) is None

        ec.jitted = False
        assert frame.f_back() is None
        ec._unchain(frame)
        assert ec.some_frame is None
        assert ec.framestackdepth == 0
        assert frame.f_back_some is None
        assert ec.gettopframe() is None


    def test_frame_chain_jitted_forced(self):

        ec = self.EC()

        assert ec.some_frame is None
        assert ec.framestackdepth == 0

        frame = self.Frame(ec)
        ec._chain(frame)
        
        ec.jitted = True
        frame2 = self.Frame(ec)
        ec._chain(frame2)

        # recursive enter/leave seen by the jit
        frame3 = self.Frame(ec)
        ec._chain(frame3)
        res = frame3.force_f_back()
        assert res is frame2

        assert frame3.f_back() is frame2
        ec._unchain(frame3)
      
        assert frame2.f_back() is frame
        ec._unchain(frame2)
        ec.jitted = False
        assert frame.f_back() is None
        ec._unchain(frame)

        assert frame3.f_back() is frame2
        assert frame2.f_back() is frame
        assert frame.f_back() is None

    def enter_two_jitted_levels(self):
        ec = self.EC()

        assert ec.some_frame is None
        assert ec.framestackdepth == 0

        frame = self.Frame(ec)
        ec._chain(frame)
        
        ec.jitted = True
        ec.virtualizable = frame
        frame2 = self.Frame(ec, frame)
        ec._chain(frame2)
        assert not frame2.escaped
        return ec, frame, frame2

    def leave_two_jitted_levels(self, ec, frame, frame2):
        assert frame2.f_back() is frame
        ec._unchain(frame2)
        ec.jitted = False
        assert frame.f_back() is None
        ec._unchain(frame)

    
    def test_check_escaping_all_inlined(self):
        ec, frame, frame2 = self.enter_two_jitted_levels()

        # recursive enter/leave seen by the jit
        frame3 = self.Frame(ec, frame)
        ec._chain(frame3)
        assert not frame2.escaped
        assert not frame3.escaped

        assert frame3.f_back() is frame2
        ec._unchain(frame3)
        assert not frame2.escaped
        self.leave_two_jitted_levels(ec, frame, frame2)
      

    def test_check_escaping_not_all_inlined_enter_leave_not_seen(self):
        ec, frame, frame2 = self.enter_two_jitted_levels()

        ec.jitted = False
        # recursive enter/leave not seen by the jit
        frame3 = self.Frame(ec)
        ec._chain(frame3)

        assert not frame2.escaped
        assert frame3.escaped

        ec._unchain(frame3)
        ec.jitted = True
        assert not frame2.escaped
      
        self.leave_two_jitted_levels(ec, frame, frame2)

    def test_check_escaping_not_all_inlined_enter_leave_seen(self):
        ec, frame, frame2 = self.enter_two_jitted_levels()

        # recursive enter/leave seen by the jit
        frame3 = self.Frame(ec, frame)
        ec._chain(frame3)
        ExecutionContext._jit_rechain_frame(ec, frame3)
        ec.jitted = False
        frame3.look_at()
        assert not frame2.escaped
        assert frame3.escaped

        ec.jitted = True
        assert frame3.f_back() is frame2
        ec._unchain(frame3)
        assert not frame2.escaped
      
        self.leave_two_jitted_levels(ec, frame, frame2)


    def test_check_escaping_multi_non_jitted_levels(self):
        ec, frame, frame2 = self.enter_two_jitted_levels()

        # recursive enter/leave seen by the jit
        frame3 = self.Frame(ec, frame)
        ec._chain(frame3)
        ExecutionContext._jit_rechain_frame(ec, frame3)
        ec.jitted = False

        assert frame3.escaped
        assert not frame2.escaped
        assert frame3.escaped

        frame4 = self.Frame(ec)
        ec._chain(frame4)
        assert ec.framestackdepth == 4

        ec._unchain(frame4)
        assert frame3.escaped
        assert not frame2.escaped

        ec.jitted = True
        assert frame3.f_back() is frame2
        ec._unchain(frame3)
        assert not frame2.escaped
      
        self.leave_two_jitted_levels(ec, frame, frame2)

    def test_check_escaping_jitted_with_two_differen_virtualizables(self):
        ec, frame, frame2 = self.enter_two_jitted_levels()

        frame3 = self.Frame(ec, frame)
        ec._chain(frame3)
        # frame3 is not inlined, but contains a loop itself, for which code has
        # been generated
        ExecutionContext._jit_rechain_frame(ec, frame3)
        ec.virtualizable = frame3

        frame3.look_at()
        assert not frame2.escaped
        assert frame3.escaped

        frame4 = self.Frame(ec, frame3)
        ec._chain(frame4)
        assert ec.framestackdepth == 4
        assert not frame4.escaped

        ec._unchain(frame4)
        assert frame3.escaped
        assert not frame2.escaped

        ec.virtualizable = frame

        ec._unchain(frame3)
        assert not frame2.escaped

