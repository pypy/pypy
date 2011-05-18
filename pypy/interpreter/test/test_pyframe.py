from pypy.tool import udir


class AppTestPyFrame:

    def setup_class(cls):
        cls.w_udir = cls.space.wrap(str(udir.udir))
        cls.w_tempfile1 = cls.space.wrap(str(udir.udir.join('tempfile1')))

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

    def test_f_lineno_set(self):
        def tracer(f, *args):
            def x(f, *args):
                f.f_lineno += 1
            return x

        def function():
            xyz
            return 3
        
        import sys
        sys.settrace(tracer)
        function()
        sys.settrace(None)
        # assert did not crash

    def test_f_lineno_set_firstline(self):
        seen = []
        def tracer(f, event, *args):
            seen.append((event, f.f_lineno))
            if len(seen) == 5:
                f.f_lineno = 1       # bug shown only when setting lineno to 1
            return tracer

        def g():
            import sys
            sys.settrace(tracer)
            exec "x=1\ny=x+1\nz=y+1\nt=z+1\ns=t+1\n" in {}
            sys.settrace(None)

        g()
        assert seen == [('call', 1),
                        ('line', 1),
                        ('line', 2),
                        ('line', 3),
                        ('line', 4),
                        ('line', 2),
                        ('line', 3),
                        ('line', 4),
                        ('line', 5),
                        ('return', 5)]

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

    def test_trace_ignore_hidden(self):
        import sys
        import _testing
            
        l = []
        def trace(a,b,c):
            l.append((a,b,c))

        def f():
            h = _testing.Hidden()
            r = h.meth()
            return r

        sys.settrace(trace)
        res = f()
        sys.settrace(None)
        assert len(l) == 1
        assert l[0][1] == 'call'
        assert res == 'hidden' # sanity

    def test_trace_hidden_prints(self):
        import sys

        l = []
        def trace(a,b,c):
            l.append((a,b,c))
            return trace

        outputf = open(self.tempfile1, 'w')
        def f():
            print >> outputf, 1
            print >> outputf, 2
            print >> outputf, 3
            return "that's the return value"

        sys.settrace(trace)
        f()
        sys.settrace(None)
        outputf.close()
        # should get 1 "call", 3 "line" and 1 "return" events, and no call
        # or return for the internal app-level implementation of 'print'
        assert len(l) == 6
        assert [what for (frame, what, arg) in l] == [
            'call', 'line', 'line', 'line', 'line', 'return']
        assert l[-1][2] == "that's the return value"

    def test_trace_return_exc(self):
        import sys
        l = []
        def trace(a,b,c): 
            if b in ('exception', 'return'):
                l.append((b, c))
            return trace

        def g():
            raise Exception            
        def f():
            try:
                g()
            except:
                pass
        sys.settrace(trace)
        f()
        sys.settrace(None)
        assert len(l) == 4
        assert l[0][0] == 'exception'
        assert isinstance(l[0][1][1], Exception)
        assert l[1] == ('return', None)
        assert l[2][0] == 'exception'
        assert isinstance(l[2][1][1], Exception)
        assert l[3] == ('return', None)

    def test_trace_raises_on_return(self):
        import sys
        def trace(frame, event, arg):
            if event == 'return':
                raise ValueError
            else:
                return trace

        def f(): return 1

        for i in xrange(sys.getrecursionlimit() + 1):
            sys.settrace(trace)
            try:
                f()
            except ValueError:
                pass

    def test_trace_try_finally(self):
        import sys
        l = []
        def trace(frame, event, arg):
            if event == 'exception':
                l.append(arg)
            return trace

        def g():
            try:
                raise Exception
            finally:
                pass

        def f():
            try:
                g()
            except:
                pass

        sys.settrace(trace)
        f()
        sys.settrace(None)
        assert len(l) == 2
        assert issubclass(l[0][0], Exception)
        assert issubclass(l[1][0], Exception)

    def test_trace_raise_three_arg(self):
        import sys
        l = []
        def trace(frame, event, arg):
            if event == 'exception':
                l.append(arg)
            return trace

        def g():
            try:
                raise Exception
            except Exception, e:
                import sys
                raise Exception, e, sys.exc_info()[2]

        def f():
            try:
                g()
            except:
                pass

        sys.settrace(trace)
        f()
        sys.settrace(None)
        assert len(l) == 2
        assert issubclass(l[0][0], Exception)
        assert issubclass(l[1][0], Exception)
        

    def test_trace_generator_finalisation(self):
        import sys
        l = []
        got_exc = []
        def trace(frame, event, arg):
            l.append((frame.f_lineno, event))
            if event == 'exception':
                got_exc.append(arg)
            return trace

        d = {}
        exec """if 1:
        def g():
            try:
                yield True
            finally:
                pass

        def f():
            try:
                gen = g()
                gen.next()
                gen.close()
            except:
                pass
        """ in d
        f = d['f']

        sys.settrace(trace)
        f()
        sys.settrace(None)
        assert len(got_exc) == 1
        assert issubclass(got_exc[0][0], GeneratorExit)
        assert l == [(8, 'call'),
                     (9, 'line'),
                     (10, 'line'),
                     (11, 'line'),
                     (2, 'call'),
                     (3, 'line'),
                     (4, 'line'),
                     (4, 'return'),
                     (12, 'line'),
                     (4, 'call'),
                     (4, 'exception'),
                     (6, 'line'),
                     (6, 'return'),
                     (12, 'return')]

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

    def test_set_unset_f_trace(self):
        import sys
        seen = []
        def trace1(frame, what, arg):
            seen.append((1, frame, frame.f_lineno, what, arg))
            return trace1
        def trace2(frame, what, arg):
            seen.append((2, frame, frame.f_lineno, what, arg))
            return trace2
        def set_the_trace(f):
            f.f_trace = trace1
            sys.settrace(trace2)
            len(seen)     # take one line: should not be traced
        f = sys._getframe()
        set_the_trace(f)
        len(seen)     # take one line: should not be traced
        len(seen)     # take one line: should not be traced
        sys.settrace(None)   # and this line should be the last line traced
        len(seen)     # take one line
        del f.f_trace
        len(seen)     # take one line
        firstline = set_the_trace.func_code.co_firstlineno
        assert seen == [(1, f, firstline + 6, 'line', None),
                        (1, f, firstline + 7, 'line', None),
                        (1, f, firstline + 8, 'line', None)]
