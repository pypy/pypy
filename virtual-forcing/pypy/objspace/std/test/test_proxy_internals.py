
""" test proxy internals like code, traceback, frame
"""
import py
from pypy.conftest import gettestobjspace, option

class AppProxy(object):
    def setup_class(cls):
        cls.space = gettestobjspace(**{"objspace.std.withtproxy": True})

    def setup_method(self, meth):
        self.w_get_proxy = self.space.appexec([], """():
        class Controller(object):
            def __init__(self, obj):
                self.obj = obj
    
            def perform(self, name, *args, **kwargs):
                return getattr(self.obj, name)(*args, **kwargs)
        def get_proxy(f):
            from __pypy__ import tproxy as proxy
            return proxy(type(f), Controller(f).perform)
        return get_proxy
        """)

class AppTestProxyInterpOnly(AppProxy):
    def setup_class(cls):
        if option.runappdirect:
            py.test.skip("interp only test")
        from pypy.interpreter.typedef import TypeDef, interp2app
        from pypy.interpreter.baseobjspace import Wrappable

        class W_Stuff(Wrappable):
            pass

        def descr_new(space, w_subtype):
            return W_Stuff()

        W_Stuff.typedef = TypeDef(
            'Stuff',
            __new__ = interp2app(descr_new),
        )
        cls.w_Stuff = cls.space.gettypefor(W_Stuff)

    def test_unproxyable(self):
        raises(TypeError, self.get_proxy, self.Stuff())

class AppTestProxyInternals(AppProxy):
    def test_traceback_basic(self):
        try:
            1/0
        except:
            import sys
            e = sys.exc_info()
        
        tb = self.get_proxy(e[2])
        assert tb.tb_frame is e[2].tb_frame

    def test_traceback_catch(self):
        try:
            try:
                1/0
            except ZeroDivisionError, e:
                ex = self.get_proxy(e)
                raise ex
        except ZeroDivisionError:
            pass
        else:
            raise AssertionError("Did not raise")

    def test_traceback_reraise(self):
        #skip("Not implemented yet")
        try:
            1/0
        except:
            import sys
            e = sys.exc_info()
        
        tb = self.get_proxy(e[2])
        raises(ZeroDivisionError, "raise e[0], e[1], tb")
        raises(ZeroDivisionError, "raise e[0], self.get_proxy(e[1]), tb")
        import traceback
        assert len(traceback.format_tb(tb)) == 1

    def test_simple_frame(self):
        import sys
        frame = sys._getframe(0)
        fp = self.get_proxy(frame)
        assert fp.f_locals == frame.f_locals

class AppTestProxyTracebackController(AppProxy):
    def test_controller(self):
        import types
        import sys
        import traceback
        
        def get_proxy(f):
            from __pypy__ import tproxy as proxy
            return proxy(type(f), Controller(f).perform)
        
        class FakeTb(object):
            def __init__(self, tb):
                self.tb_lasti = tb.tb_lasti
                self.tb_lineno = tb.tb_lineno
                if tb.tb_next:
                    self.tb_next = FakeTb(tb.tb_next)
                else:
                    self.tb_next = None
                self.tb_frame = get_proxy(tb.tb_frame)
        
        class Controller(object):
            def __init__(self, tb):
                if isinstance(tb, types.TracebackType):
                    self.obj = FakeTb(tb)
                else:
                    self.obj = tb
            
            def perform(self, name, *args, **kwargs):
                return getattr(self.obj, name)(*args, **kwargs)
        
        def f():
            1/0
        
        def g():
            f()
        
        try:
            g()
        except:
            e = sys.exc_info()
        
        last_tb = e[2]
        tb = get_proxy(e[2])
        try:
            raise e[0], e[1], tb
        except:
            e = sys.exc_info()
        
        assert traceback.format_tb(last_tb) == traceback.format_tb(e[2])
    
    def test_proxy_get(self):
        from __pypy__ import tproxy, get_tproxy_controller
        l = [1,2,3]
        def f(name, *args, **kwargs):
            return getattr(l, name)(*args, **kwargs)
        lst = tproxy(list, f)
        assert get_tproxy_controller(lst) is f

    def test_proxy_file(self):
        from __pypy__ import tproxy

        def f(name, *args, **kwds):
            pass

        t = tproxy(file, f)
