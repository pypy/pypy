
import py
from pypy.rpython.lltypesystem.lltype import typeOf, Ptr, PyObject
from pypy.rpython.rtyper import RPythonTyper
from pypy.rpython.llinterp import LLInterpreter, LLException,log
from pypy.rpython.rint import signed_repr
from pypy.rpython.lltypesystem import rstr
from pypy.annotation.model import lltype_to_annotation
from pypy.rlib.rarithmetic import r_uint, ovfcheck
from pypy.rpython.memory.lltypesimulation import pyobjectptr
from pypy.rpython.memory import gclltype

from pypy.rpython.test.test_llinterp import timelog, gengraph

def setup_module(mod):
    mod.logstate = py.log._getstate()
    py.log.setconsumer("llinterp", py.log.STDOUT)

def teardown_module(mod):
    py.log._setstate(mod.logstate)


_lastinterpreted = []
_tcache = {}
def get_interpreter(func, values, view=False, viewbefore=False, policy=None,
                    someobjects=False):
    key = (func,) + tuple([typeOf(x) for x in values])+ (someobjects,)
    try: 
        (t, interp, graph) = _tcache[key]
    except KeyError:
        def annotation(x):
            T = typeOf(x)
            if T == Ptr(PyObject) and someobjects:
                return object
            elif T == Ptr(rstr.STR):
                return str
            else:
                return lltype_to_annotation(T)
        
        t, typer, graph = gengraph(func, [annotation(x)
                      for x in values], viewbefore, policy)
        interp = LLInterpreter(typer, heap=gclltype, malloc_check=False)
        _tcache[key] = (t, interp, graph)
        # keep the cache small 
        _lastinterpreted.append(key) 
        if len(_lastinterpreted) >= 4: 
            del _tcache[_lastinterpreted.pop(0)]
    if view:
        t.view()
    return interp, graph
    
def interpret(func, values, view=False, viewbefore=False, policy=None,
              someobjects=False):
    interp, graph = get_interpreter(func, values, view, viewbefore, policy,
                             someobjects)
    return interp.eval_graph(graph, values)

def interpret_raises(exc, func, values, view=False, viewbefore=False, policy=None, someobjects=False):
    interp, graph = get_interpreter(func, values, view, viewbefore, policy,
                             someobjects)
    info = py.test.raises(LLException, "interp.eval_graph(graph, values)")
    assert interp.find_exception(info.value) is exc, "wrong exception type"

#__________________________________________________________________
# tests

def test_int_ops():
    res = interpret(number_ops, [3])
    assert res == 4

def test_invert():
    def f(x):
        return ~x
    res = interpret(f, [3])
    assert res == ~3
    assert interpret(f, [r_uint(3)]) == ~r_uint(3)

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
    interpret_raises(IndexError, raise_exception, [42])
    interpret_raises(ValueError, raise_exception, [43])

def test_call_raise():
    res = interpret(call_raise, [41])
    assert res == 41
    interpret_raises(IndexError, call_raise, [42])
    interpret_raises(ValueError, call_raise, [43])

def test_call_raise_twice():
    res = interpret(call_raise_twice, [6, 7])
    assert res == 13
    interpret_raises(IndexError, call_raise_twice, [6, 42])
    res = interpret(call_raise_twice, [6, 43])
    assert res == 1006
    interpret_raises(IndexError, call_raise_twice, [42, 7])
    interpret_raises(ValueError, call_raise_twice, [43, 7])

def test_call_raise_intercept():
    res = interpret(call_raise_intercept, [41], view=False)
    assert res == 41
    res = interpret(call_raise_intercept, [42])
    assert res == 42
    interpret_raises(TypeError, call_raise_intercept, [43])

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
    items = res.ll_items()
    assert len(items) == len([1,2,3])
    for i in range(3):
        assert items[i] == i+1

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
    items = res.ll_items()
    assert len(items) == len([3,2,1])
    print res
    for i in range(3):
        assert items[i] == 3-i
        
def test_list_pop():
    def f():
        l = [1,2,3]
        l1 = l.pop(2)
        l2 = l.pop(1)
        l3 = l.pop(-1)
        return [l1,l2,l3]
    res = interpret(f,[])
    items = res.ll_items()
    assert len(items) == 3

def test_obj_obj_add():
    def f(x,y):
        return x+y
    _1L = pyobjectptr(1L)
    _2L = pyobjectptr(2L)
    res = interpret(f, [_1L, _2L], someobjects=True)
    assert res._obj.value == 3L

def test_ovf():
    import sys
    def f(x):
        try:
            return ovfcheck(sys.maxint + x)
        except OverflowError:
            return 1
    res = interpret(f, [1])
    assert res == 1
    res = interpret(f, [0])
    assert res == sys.maxint
    def g(x):
        try:
            return ovfcheck(abs(x))
        except OverflowError:
            return 42
    res = interpret(g, [-sys.maxint - 1])
    assert res == 42
    res = interpret(g, [-15])
    assert res == 15

def test_div_ovf_zer():
    import sys
    def f(x):
        try:
            return ovfcheck((-sys.maxint - 1) // x)
        except OverflowError:
            return 1
        except ZeroDivisionError:
            return 0
    res = interpret(f, [0])
    assert res == 0
    res = interpret(f, [-1])
    assert res == 1
    res = interpret(f, [30])
    assert res == (-sys.maxint - 1) // 30

def test_mod_ovf_zer():
    import sys
    def f(x):
        try:
            return ovfcheck((-sys.maxint - 1) % x)
        except OverflowError:
            return 1
        except ZeroDivisionError:
            return 0
    res = interpret(f, [0])
    assert res == 0
    res = interpret(f, [-1])
    assert res == 1
    res = interpret(f, [30])
    assert res == (-sys.maxint - 1) % 30


def test_obj_obj_is():
    def f(x,y):
        return x is y
    o = pyobjectptr(object())
    res = interpret(f, [o, o], someobjects=True)
    assert res is True
    
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

def test_id():
    def getids(i, j):
        e1 = ExampleClass(1)
        e2 = ExampleClass(2)
        a = [e1, e2][i]
        b = [e1, e2][j]
        return (id(a) == id(b)) == (a is b)
    for i in [0, 1]:
        for j in [0, 1]:
            result = interpret(getids, [i, j])
            assert result


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


#the following function has a constant argument which is void
def test_str_of_int():
    def dummy(i):
        return str(i)
    
    res = interpret(dummy, [0])
    assert ''.join(res.chars) == '0'

    res = interpret(dummy, [1034])
    assert ''.join(res.chars) == '1034'

    res = interpret(dummy, [-123])
    assert ''.join(res.chars) == '-123'


