
import sys
from py.test import main
from py.__impl__.magic.exprinfo import getmsg, interpret

def getexcinfo(exc, obj, *args, **kwargs):
    try:
        obj(*args, **kwargs)
    except KeyboardInterrupt:
        raise
    except exc:
        return sys.exc_info()
    else:
        raise AssertionError, "%r(*%r, **%r) did not raise" %(
            obj, args, kwargs)

def test_assert_exprinfo():
    def g():
        a = 1
        b = 2
        assert a == b
    excinfo = getexcinfo(AssertionError, g)
    msg = getmsg(excinfo)
    assert msg == 'AssertionError: assert 1 == 2'

def test_assert_func_argument_type_error(): 
    def f (): 
        pass
    def g():
        f(1) 
    excinfo = getexcinfo(TypeError, g)
    msg = getmsg(excinfo)
    assert msg.find("takes no argument") != -1

    class A: 
        def f():
            pass 
    def g():
        A().f()
    excinfo = getexcinfo(TypeError, g)
    msg = getmsg(excinfo)
    assert msg.find("takes no argument") != -1

    def g():
        A.f()
    excinfo = getexcinfo(TypeError, g)
    msg = getmsg(excinfo)
    assert msg.find("must be called with A") != -1

def global_f():
    return 42

def test_exprinfo_funccall():
    def g():
        assert global_f() == 43
    excinfo = getexcinfo(AssertionError, g)
    msg = getmsg(excinfo)
    assert msg == 'AssertionError: assert 42 == 43\n +  where 42 = global_f()'

def test_keyboard_interrupt():
    # XXX this test is slightly strange because it is not
    # clear that "interpret" should execute "raise" statements
    # ... but it apparently currently does and it's nice to 
    # exercise the code because the exprinfo-machinery is 
    # not much executed when all tests pass ... 
    
    class DummyFrame: 
        f_globals = f_locals = {}
    for exstr in "SystemExit", "KeyboardInterrupt", "MemoryError":
        ex = eval(exstr) 
        try:
            interpret("raise %s" % exstr, DummyFrame) 
        except ex: 
            pass
        else:
            raise AssertionError, "ex %s didn't pass through" %(exstr, )
        
main()
