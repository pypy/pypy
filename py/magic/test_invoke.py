import __builtin__ as bltin 
import py 
import inspect

def check_dyncode():
    co = compile('x=3', 'bogus', 'exec') 
    s = inspect.getfile(co) 
    assert s
    line = inspect.getsource(co) 
    assert line.strip() == "x=3" 

def check_assertion():
    excinfo = py.test.raises(AssertionError, "assert 1 == 2")
    value = excinfo[1]
    assert str(value) == "assert 1 == 2" 

def test_invoke_dyncode():
    old = compile
    py.magic.invoke(dyncode=True)
    try:
        assert compile != old 
        check_dyncode()
    finally:
        py.magic.revoke(dyncode=True) 
    
def test_invoke_assertion():
    py.magic.invoke(assertion=True)
    try:
        check_assertion()
    finally:
        py.magic.revoke(assertion=True)
    
