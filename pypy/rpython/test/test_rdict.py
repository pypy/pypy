
from pypy.rpython import lltype 
from pypy.rpython.test.test_llinterp import interpret 

import py

def test_dict_creation(): 
    def createdict(i): 
        d = {'hello' : i}
        return d['hello']

    res = interpret(createdict, [42])
    assert res == 42
