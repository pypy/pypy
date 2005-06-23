
from pypy.rpython import lltype 
from pypy.rpython.test.test_llinterp import interpret 
from pypy.rpython import rstr, rdict

import py

def test_dict_creation(): 
    def createdict(i): 
        d = {'hello' : i}
        return d['hello']

    res = interpret(createdict, [42])
    assert res == 42

def test_dict_getitem_setitem(): 
    def func(i): 
        d = {'hello' : i}
        d['world'] = i + 1
        return d['hello'] * d['world'] 
    res = interpret(func, [6])
    assert res == 42

def test_dict_getitem_keyerror(): 
    def func(i): 
        d = {'hello' : i}
        try:
            return d['world']
        except KeyError:
            return 0 
    res = interpret(func, [6])
    assert res == 0

def test_dict_del_simple():
    def func(i): 
        d = {'hello' : i}
        d['world'] = i + 1
        del d['hello']
        return len(d) 
    res = interpret(func, [6])
    assert res == 1

def test_empty_strings():
    def func(i): 
        d = {'' : i}
        del d['']
        try:
            d['']
            return 0
        except KeyError:
            pass
        return 1
    res = interpret(func, [6])
    assert res == 1
    
    def func(i): 
        d = {'' : i}
        del d['']
        d[''] = i + 1
        return len(d)
    res = interpret(func, [6])
    assert res == 1

def test_deleted_entry_reusage_with_colliding_hashes(): 
    def lowlevelhash(value): 
        p = lltype.malloc(rstr.STR, len(value))
        for i in range(len(value)):
            p.chars[i] = value[i]
        return rstr.ll_strhash(p) 
    
    def func(c1, c2): 
        c1 = chr(c1) 
        c2 = chr(c2) 
        d = {}
        d[c1] = 1
        d[c2] = 2 
        del d[c1]
        return d[c2]

    base = 8
    x = 'a'
    xh = lowlevelhash(x) % base
    for y in range(ord('b'), ord('z')): 
        if lowlevelhash(chr(y)) % base == xh: 
            break 
    else: 
        py.test.skip("XXX improve hash finding algo") 
       
    res = interpret(func, [ord(x), y])
    assert res == 2

    def func2(c1, c2): 
        c1 = chr(c1) 
        c2 = chr(c2) 
        d = {}
        d[c1] = 1
        d[c2] = 2 
        del d[c1]
        d[c1] = 3
        return d 

    res = interpret(func2, [ord(x), y])
    for i in range(len(res.entries)): 
        assert res.entries[i].key != rdict.deleted_entry_marker
