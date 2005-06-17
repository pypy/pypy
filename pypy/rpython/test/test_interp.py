
import py
from pypy.rpython.lltype import typeOf
from pypy.rpython.rtyper import RPythonTyper 
from pypy.rpython.interp import LLInterpreter, RPythonError
from pypy.translator.translator import Translator 
from pypy.rpython.lltype import pyobjectptr

# switch on logging of interp to show more info on failing tests

def setup_module(mod): 
    mod.logstate = py.log._getstate()
    py.log.setconsumer("llinterp", py.log.STDOUT) 

def teardown_module(mod): 
    py.log._setstate(mod.logstate) 

def find_exception(exc):
    assert isinstance(exc, RPythonError)
    import exceptions
    klass, inst = exc.args
    func = typer.getexceptiondata().ll_pyexcclass2exc
    for cls in exceptions.__dict__.values():
        if type(cls) is type(Exception):
            if func(pyobjectptr(cls)).typeptr == klass:
                return cls

def gengraph(func, argtypes=[]): 
    t = Translator(func)
    t.annotate(argtypes)
    global typer # we need it for find_exception
    typer = RPythonTyper(t.annotator)
    typer.specialize()
    #t.view()
    t.checkgraphs()
    return t, typer

def interpret(func, values): 
    t, typer = gengraph(func, [type(x) for x in values])
    interp = LLInterpreter(t.flowgraphs, typer)
    res = interp.eval_function(func, values) 
    return res 

#__________________________________________________________________
# tests 
    
def test_int_ops(): 
    res = interpret(number_ops, [3])
    assert res == 4 

def test_float_ops(): 
    res = interpret(number_ops, [3.5])
    assert res == 4.5 

def test_ifs(): 
    res = interpret(simple_ifs, [0])
    assert res == 43 
    res = interpret(simple_ifs, [1])
    assert res == 42 

def test_raise():
    res = interpret(raise_exception, [41])
    assert res == 41
    info = raises(RPythonError, interpret, raise_exception, [42])
    assert find_exception(info.value) is IndexError
    info = raises(RPythonError, interpret, raise_exception, [43])
    assert find_exception(info.value) is ValueError

def test_call_raise():
    res = interpret(call_raise, [41])
    assert res == 41
    info = raises(RPythonError, interpret, call_raise, [42])
    assert find_exception(info.value) is IndexError
    info = raises(RPythonError, interpret, call_raise, [43])
    assert find_exception(info.value) is ValueError

def test_call_raise_intercept():
    res = interpret(call_raise_intercept, [41])
    assert res == 41
    res = interpret(call_raise_intercept, [42])
    assert res == 42
    info = raises(RPythonError, interpret, call_raise_intercept, [43])
    assert find_exception(info.value) is TypeError

def test_while_simple(): 
    res = interpret(while_simple, [3])
    assert res == 6

def test_number_comparisons(): 
    for t in float, int: 
        val1 = t(3)
        val2 = t(4)
        gcres = interpret(comparisons, [val1, val2])
        res = [getattr(gcres, x) for x in typeOf(gcres).TO._names]
        assert res == [True, True, False, True, False, False]

def XXXtest_some_builtin(): 
    def f(i, j): 
        x = range(i) 
        return x[j]
    res = interpret(f, [10, 7])
    assert res == 6

#
#__________________________________________________________________
#
#  Test lists
def test_list_creation():
    def f():
        return [1,2,3]
    res = interpret(f,[])
    assert len(res.items) == len([1,2,3])
    for i in range(3):
        assert res.items[i] == i+1
#__________________________________________________________________
# example functions for testing the LLInterpreter 
_snap = globals().copy()

def number_ops(i): 
    j = i + 2
    k = j * 2 
    m = k / 2
    return m - 1

def comparisons(x, y): 
    return (x < y, 
            x <= y, 
            x == y, 
            x != y, 
            #x is None,  
            #x is not None, 
            x >= y, 
            x > y, 
            )

def simple_ifs(i): 
    if i: 
        return 42 
    else: 
        return 43 

def while_simple(i): 
    sum = 0
    while i > 0: 
        sum += i
        i -= 1
    return sum

def raise_exception(i):
    if i == 42:
        raise IndexError
    elif i == 43:
        raise ValueError
    return i

def call_raise(i):
    return raise_exception(i)

def call_raise_intercept(i):
    try:
        return raise_exception(i)
    except IndexError:
        return i
    except ValueError:
        raise TypeError
#__________________________________________________________________
# interactive playing 

if __name__ == '__main__': 
    try:
        import rlcompleter2 as _rl2
        _rl2.setup() 
    except ImportError: 
        pass

    t, typer = gengraph(number_ops, [int])
    interp = LLInterpreter(t.flowgraphs, typer)
    res = interp.eval_function(number_ops, [3])
    assert res == number_ops(3)
    for name, value in globals().items(): 
        if name not in _snap and name[0] != '_': 
            print "%20s: %s" %(name, value)


