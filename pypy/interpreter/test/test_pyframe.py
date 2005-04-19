import autopath


class AppTestPyFrame:

    # test for the presence of the attributes, not functionality

##     def test_f_locals(self):
##         import sys
##         f = sys._getframe()
##         assert f.f_locals is locals()

##     def test_f_globals(self):
##         import sys
##         f = sys._getframe()
##         assert f.f_globals is globals()

    def test_f_builtins(self):
        import sys, __builtin__
        f = sys._getframe()
        assert f.f_builtins is __builtin__.__dict__

    def test_f_code(self):
        def g():
            import sys
            f = sys._getframe()
            return f.f_code
        assert g() is g.func_code

    def test_f_lineno(self):
        def g():
            import sys
            f = sys._getframe()
            x = f.f_lineno
            y = f.f_lineno
            z = f.f_lineno
            return [x, y, z]
        origin = g.func_code.co_firstlineno
        assert g() == [origin+3, origin+4, origin+5]

    def test_f_back(self):
            import sys
            def trace(a,b,c): return trace
            def f():
                f_frame = sys._getframe()
                return g(f_frame)
            def g(f_frame):
                g_frame = sys._getframe()
                print g_frame
                print g_frame.f_back
                print g_frame.f_back.f_code.co_name, f_frame.f_code.co_name 
            sys.settrace(trace)
            f()

    def test_trace_exc(self):
        import sys
        l = []
        def ltrace(a,b,c): 
            if b == 'exception':
                l.append(c)
            return ltrace
        def trace(a,b,c): return ltrace
        def f():
            try:
                raise Exception
            except:
                pass
        sys.settrace(trace)
        f()
        sys.settrace(None)
        assert len(l) == 1
        assert isinstance(l[0][1], Exception)

