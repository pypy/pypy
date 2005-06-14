
import py
py.magic.autopath()
from pypy.rpython.rtyper import RPythonTyper 
from pypy.rpython.interp import LLInterpreter 
from pypy.translator.translator import Translator 

def gengraph(func, argtypes=[]): 
    t = Translator(func)
    t.annotate(argtypes)
    typer = RPythonTyper(t.annotator)
    typer.specialize()
    #t.view()
    t.checkgraphs()
    return t

#__________________________________________________________________
# tests 
    
def test_int_ops(): 
    t = gengraph(number_ops, [int])
    interp = LLInterpreter(t.flowgraphs)
    res = interp.eval_function(number_ops, [3])
    assert res == 4 

def test_float_ops(): 
    t = gengraph(number_ops, [float])
    interp = LLInterpreter(t.flowgraphs)
    res = interp.eval_function(number_ops, [3.5])
    assert res == 4.5 

def interpret(func, values): 
    t = gengraph(func, [type(x) for x in values])
    interp = LLInterpreter(t.flowgraphs)
    res = interp.eval_function(func, values) 
    return res 

def test_ifs(): 
    res = interpret(simple_ifs, [0])
    assert res == 43 
    res = interpret(simple_ifs, [1])
    assert res == 42 

def test_while_simple(): 
    res = interpret(while_simple, [3])
    assert res == 6
    
    
#__________________________________________________________________
# example functions for testing the LLInterpreter 
_snap = globals().copy()

def number_ops(i): 
    j = i + 2
    k = j * 2 
    m = k / 2
    return m - 1

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

#__________________________________________________________________
# interactive playing 

if __name__ == '__main__': 
    try:
        import rlcompleter2 as _rl2
        _rl2.setup() 
    except ImportError: 
        pass

    t = gengraph(number_ops, [int])
    interp = LLInterpreter(t.flowgraphs)
    res = interp.eval_function(number_ops, [3])
    assert res == 6 
    for name, value in globals().items(): 
        if name not in _snap and name[0] != '_': 
            print "%20s: %s" %(name, value)


