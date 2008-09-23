
class AppTestPyFrame:

    # test for the presence of the attributes, not functionality

    def test_f_locals(self):
        import sys
        f = sys._getframe()
        assert f.f_locals is locals()

    def test_f_globals(self):
        import sys
        f = sys._getframe()
        assert f.f_globals is globals()

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

    def test_f_trace_del(self): 
        import sys
        f = sys._getframe() 
        del f.f_trace 
        assert f.f_trace is None

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
        def f():
            assert sys._getframe().f_code.co_name == g()
        def g():
            return sys._getframe().f_back.f_code.co_name 
        f()

    def test_f_exc_xxx(self):
        import sys

        class OuterException(Exception):
            pass
        class InnerException(Exception):
            pass

        def g(exc_info):
            f = sys._getframe()
            assert f.f_exc_type is None
            assert f.f_exc_value is None
            assert f.f_exc_traceback is None
            try:
                raise InnerException
            except:
                assert f.f_exc_type is exc_info[0]
                assert f.f_exc_value is exc_info[1]
                assert f.f_exc_traceback is exc_info[2]
        try:
            raise OuterException
        except:
            g(sys.exc_info())

    def test_trace_basic(self):
        import sys
        l = []
        class Tracer:
            def __init__(self, i):
                self.i = i
            def trace(self, frame, event, arg):
                l.append((self.i, frame.f_code.co_name, event, arg))
                if frame.f_code.co_name == 'g2':
                    return None    # don't trace g2
                return Tracer(self.i+1).trace
        def g3(n):
            n -= 5
            return n
        def g2(n):
            n += g3(2)
            n += g3(7)
            return n
        def g(n):
            n += g2(3)
            return n
        def f(n):
            n = g(n)
            return n * 7
        sys.settrace(Tracer(0).trace)
        x = f(4)
        sys.settrace(None)
        assert x == 42
        print l
        assert l == [(0, 'f', 'call', None),
                     (1, 'f', 'line', None),
                         (0, 'g', 'call', None),
                         (1, 'g', 'line', None),
                             (0, 'g2', 'call', None),
                                 (0, 'g3', 'call', None),
                                 (1, 'g3', 'line', None),
                                 (2, 'g3', 'line', None),
                                 (3, 'g3', 'return', -3),
                                 (0, 'g3', 'call', None),
                                 (1, 'g3', 'line', None),
                                 (2, 'g3', 'line', None),
                                 (3, 'g3', 'return', 2),
                         (2, 'g', 'line', None),
                         (3, 'g', 'return', 6),
                     (2, 'f', 'line', None),
                     (3, 'f', 'return', 42)]

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

    def test_dont_trace_on_reraise(self):
        import sys
        l = []
        def ltrace(a,b,c): 
            if b == 'exception':
                l.append(c)
            return ltrace
        def trace(a,b,c): return ltrace
        def f():
            try:
                1/0
            except:
                try:
                    raise
                except:
                    pass
        sys.settrace(trace)
        f()
        sys.settrace(None)
        assert len(l) == 1
        assert issubclass(l[0][0], Exception)

    def test_dont_trace_on_raise_with_tb(self):
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
                return sys.exc_info()
        def g():
            exc, val, tb = f()
            try:
                raise exc, val, tb
            except:
                pass
        sys.settrace(trace)
        g()
        sys.settrace(None)
        assert len(l) == 1
        assert isinstance(l[0][1], Exception)

    def test_trace_changes_locals(self):
        import sys
        def trace(frame, what, arg):
            frame.f_locals['x'] = 42
            return trace
        def f(x):
            return x
        sys.settrace(trace)
        res = f(1)
        sys.settrace(None)
        assert res == 42
