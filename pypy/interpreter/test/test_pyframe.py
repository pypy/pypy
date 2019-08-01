from pypy.conftest import option
from pypy.interpreter.gateway import interp2app

def check_no_w_locals(space, w_frame):
    return space.wrap(w_frame.getorcreatedebug().w_locals is None)

class AppTestPyFrame:

    def setup_class(cls):
        space = cls.space
        if not option.runappdirect:
            w_call_further = cls.space.appexec([], """():
                def call_further(f):
                    return f()
                return call_further
            """)
            assert not w_call_further.code.hidden_applevel
            w_call_further.code.hidden_applevel = True       # hack
            cls.w_call_further = w_call_further

            cls.w_check_no_w_locals = space.wrap(interp2app(check_no_w_locals))

    # test for the presence of the attributes, not functionality

    def test_f_back_hidden(self):
        if not hasattr(self, 'call_further'):
            skip("not for runappdirect testing")
        import sys
        def f():
            return (sys._getframe(0),
                    sys._getframe(1),
                    sys._getframe(0).f_back)
        def main():
            return self.call_further(f)
        f0, f1, f1bis = main()
        assert f0.f_code.co_name == 'f'
        assert f1.f_code.co_name == 'main'
        assert f1bis is f1
        assert f0.f_back is f1

    def test_fast2locals_called_lazily(self):
        import sys
        class FrameHolder:
            pass
        fh = FrameHolder()
        def trace(frame, what, arg):
            # trivial trace function, does not access f_locals
            fh.frame = frame
            return trace
        def f(x):
            x += 1
            return x
        sys.settrace(trace)
        res = f(1)
        sys.settrace(None)
        assert res == 2
        if hasattr(self, "check_no_w_locals"): # not appdirect
            assert self.check_no_w_locals(fh.frame)
