import autopath
from py.__.magic import exprinfo
from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import app2interp_temp
from pypy.interpreter.argument import Arguments
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.pyframe import PyFrame
from pypy.tool.pytestsupport import AppFrame, build_pytest_assertion, AppExceptionInfo


def somefunc(x):
    print x

def test_AppFrame(space):
    import sys
    co = PyCode(space)._from_code(somefunc.func_code)
    pyframe = PyFrame(space, co, space.newdict([]), None)
    runner = AppFrame(pyframe)
    exprinfo.run("f = lambda x: x+1", runner)
    msg = exprinfo.interpret("assert isinstance(f(2), float)", runner)
    assert msg.startswith("assert isinstance(3, float)\n"
                          " +  where 3 = ")


def test_myexception(space):
    def app_test_func():
        x = 6*7
        assert x == 43
    t = app2interp_temp(app_test_func)
    f = t.get_function(space)
    space.setitem(space.builtin.w_dict, space.wrap('AssertionError'), 
                  build_pytest_assertion(space))
    try:
        f.call_args(Arguments([]))
    except OperationError, e:
        assert e.match(space, space.w_AssertionError)
        assert space.unwrap(space.str(e.w_value)) == 'assert 42 == 43'
    else:
        assert False, "got no exception!"

def app_test_exception(): 
    try: 
        raise AssertionError("42")
    except AssertionError: 
        pass 
    else: 
        raise AssertionError, "app level AssertionError mixup!"
    
def app_test_exception_with_message():
    try:
        assert 0, "Failed"
    except AssertionError, e:
        assert e.msg == "Failed"


def test_appexecinfo(space): 
    try: 
        space.appexec([], "(): raise ValueError") 
    except OperationError, e: 
        appex = AppExceptionInfo(space, e)
    else: 
        py.test.fail("did not raise!") 
    assert appex.exconly().find('ValueError') != -1 
    assert appex.exconly(tryshort=True).find('ValueError') != -1 
    assert appex.errisinstance(ValueError) 
    assert not appex.errisinstance(RuntimeError) 
    class A: 
        pass
    assert not appex.errisinstance(A) 

    
