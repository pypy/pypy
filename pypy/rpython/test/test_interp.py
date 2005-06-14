
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
    
def test_int_adding(): 
    t = gengraph(int_adding, [int])
    interp = LLInterpreter(t.flowgraphs)
    res = interp.eval_function(int_adding, [3])
    assert res == 6 

#__________________________________________________________________
# example functions for testing the LLInterpreter 
_snap = globals().copy()

def int_adding(i): 
    j = i + 2
    return j + 1 



#__________________________________________________________________
# interactive playing 

if __name__ == '__main__': 
    try:
        import rlcompleter2 as _rl2
        _rl2.setup() 
    except ImportError: 
        pass

    t = gengraph(int_adding, [int])
    interp = LLInterpreter(t.flowgraphs)
    res = interp.eval_function(int_adding, [3])
    assert res == 6 
    for name, value in globals().items(): 
        if name not in _snap and name[0] != '_': 
            print "%20s: %s" %(name, value)


