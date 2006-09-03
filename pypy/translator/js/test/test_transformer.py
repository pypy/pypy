
""" some javascript transform test examples
"""

from pypy.translator.js.main import rpython2javascript
from pypy.translator.js.test.runtest import compile_function
from pypy.translator.transformer.debug import traceback_handler

def test_simple_tansform():
    def g():
        raise ValueError()
    
    def f():
        g()
    
    def wrapper():
        try:
            # XXX: this is needed to make annotator happy
            traceback_handler.enter("entrypoint", "data")
            f()
        except:
            return "|".join([i + ": " + j for i, j in traceback_handler.tb])
        return ""
    
    fn = compile_function(wrapper, [], debug_transform = True)
    retval = fn()
    lst = retval.split('|')
    assert len(lst) == 3
    assert lst[1] == 'f: ()'
    assert lst[2] == 'g: ()'

def test_simple_seq():
    def fun(i):
        if i:
            a = [("ab", "cd"), ("ef", "xy")]
        else:
            a = [("xz", "pr"), ("as", "fg")]
        return ",".join(["%s : %s" % (i, j) for i,j in a])
    
    fn = compile_function(fun, [int])
    assert fn(0) == fun(0)
    assert fn(1) == fun(1)
