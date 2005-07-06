
import py
from pypy.rpython.lltype import typeOf,pyobjectptr
from pypy.rpython.rtyper import RPythonTyper
from pypy.rpython.llinterp import LLInterpreter, LLException,log
from pypy.translator.translator import Translator
from pypy.rpython.rlist import *
from pypy.rpython.rint import signed_repr
from pypy.annotation.model import lltype_to_annotation

# switch on logging of interp to show more info on failing tests

def setup_module(mod):
    mod.logstate = py.log._getstate()
    py.log.setconsumer("llinterp", py.log.STDOUT)

def teardown_module(mod):
    py.log._setstate(mod.logstate)

def find_exception(exc):
    assert isinstance(exc, LLException)
    import exceptions
    klass, inst = exc.args
    func = typer.getexceptiondata().ll_pyexcclass2exc
    for cls in exceptions.__dict__.values():
        if type(cls) is type(Exception):
            if func(pyobjectptr(cls)).typeptr == klass:
                return cls

def timelog(prefix, call, *args, **kwds): 
    #import time
    #print prefix, "...", 
    #start = time.time()
    res = call(*args, **kwds) 
    #elapsed = time.time() - start 
    #print "%.2f secs" %(elapsed,)
    return res 

def gengraph(func, argtypes=[], viewbefore=False, policy=None):
    t = Translator(func)

    timelog("annotating", t.annotate, argtypes, policy=policy)
    if viewbefore:
        t.annotator.simplify()
        t.view()
    global typer # we need it for find_exception
    typer = RPythonTyper(t.annotator)
    timelog("rtyper-specializing", typer.specialize) 
    #t.view()
    timelog("checking graphs", t.checkgraphs) 
    return t, typer

_lastinterpreted = []
_tcache = {}
def interpret(func, values, view=False, viewbefore=False, policy=None):
    key = (func,) + tuple([typeOf(x) for x in values])
    try: 
        (t, interp) = _tcache[key]
    except KeyError: 
        t, typer = gengraph(func, [lltype_to_annotation(typeOf(x)) 
                      for x in values], viewbefore, policy)
        interp = LLInterpreter(t.flowgraphs, typer)
        _tcache[key] = (t, interp)
        # keep the cache small 
        _lastinterpreted.append(key) 
        if len(_lastinterpreted) >= 4: 
            del _tcache[_lastinterpreted.pop(0)]
    if view:
        t.view()
    return interp.eval_function(func, values)

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
    info = raises(LLException, interpret, raise_exception, [42])
    assert find_exception(info.value) is IndexError
    info = raises(LLException, interpret, raise_exception, [43])
    assert find_exception(info.value) is ValueError

def test_call_raise():
    res = interpret(call_raise, [41])
    assert res == 41
    info = raises(LLException, interpret, call_raise, [42])
    assert find_exception(info.value) is IndexError
    info = raises(LLException, interpret, call_raise, [43])
    assert find_exception(info.value) is ValueError

def test_call_raise_twice():
    res = interpret(call_raise_twice, [6, 7])
    assert res == 13
    info = raises(LLException, interpret, call_raise_twice, [6, 42])
    assert find_exception(info.value) is IndexError
    res = interpret(call_raise_twice, [6, 43])
    assert res == 1006
    info = raises(LLException, interpret, call_raise_twice, [42, 7])
    assert find_exception(info.value) is IndexError
    info = raises(LLException, interpret, call_raise_twice, [43, 7])
    assert find_exception(info.value) is ValueError

def test_call_raise_intercept():
    res = interpret(call_raise_intercept, [41], view=False)
    assert res == 41
    res = interpret(call_raise_intercept, [42])
    assert res == 42
    info = raises(LLException, interpret, call_raise_intercept, [43])
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

def test_some_builtin():
    def f(i, j):
        x = range(i)
        return x[j-1]
    res = interpret(f, [10, 7])
    assert res == 6

def test_recursion_does_not_overwrite_my_variables():
    def f(i):
        j = i + 1
        if i > 0:
            f(i-1)
        return j

    res = interpret(f, [4])
    assert res == 5

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

def test_list_itemops():
    def f(i):
        l = [1, i]
        l[0] = 0
        del l[1]
        return l[-1]
    res = interpret(f, [3])
    assert res == 0

def test_list_append():
    def f(i):
        l = [1]
        l.append(i)
        return l[0] + l[1]
    res = interpret(f, [3])
    assert res == 4

def test_list_extend():
    def f(i):
        l = [1]
        l.extend([i])
        return l[0] + l[1]
    res = interpret(f, [3])
    assert res == 4

def test_list_multiply():
    def f(i):
        l = [i]
        l = l * i  # uses alloc_and_set for len(l) == 1
        return len(l)
    res = interpret(f, [3])
    assert res == 3

def test_unicode():
    def f():
        return u'Hello world'
    res = interpret(f,[])
    
    assert res._obj.value == u'Hello world'
    
##def test_unicode_split():
##    def f():
##        res = u'Hello world'.split()
##        return u' '.join(res)
##    res = interpret(f,[],True)
##    
##    assert res == u'Hello world'

def test_list_reverse():
    def f():
        l = [1,2,3]
        l.reverse()
        return l
    res = interpret(f,[])
    assert len(res.items) == len([3,2,1])
    print res
    for i in range(3):
        assert res.items[i] == 3-i
        
def test_list_pop():
    def f():
        l = [1,2,3]
        l1 = l.pop(2)
        l2 = l.pop(1)
        l3 = l.pop(-1)
        return [l1,l2,l3]
    res = interpret(f,[])
    assert len(res.items) == 3
    
#__________________________________________________________________
#
#  Test objects and instances

class ExampleClass:
    def __init__(self, x):
        self.x = x + 1

def test_basic_instantiation():
    def f(x):
        return ExampleClass(x).x
    res = interpret(f, [4])
    assert res == 5


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

def call_raise_twice(i, j):
    x = raise_exception(i)
    try:
        y = raise_exception(j)
    except ValueError:
        y = 1000
    return x + y

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


