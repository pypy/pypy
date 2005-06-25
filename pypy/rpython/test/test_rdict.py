
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

    char_by_hash = {}
    base = rdict.STRDICT_INITSIZE
    for y in range(0, 256):
        y = chr(y)
        y_hash = lowlevelhash(y) % base 
        char_by_hash.setdefault(y_hash, []).append(y)

    x, y = char_by_hash[0][:2]   # find a collision
       
    res = interpret(func, [ord(x), ord(y)])
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

    res = interpret(func2, [ord(x), ord(y)])
    for i in range(len(res.entries)): 
        assert res.entries[i].key != rdict.deleted_entry_marker

    def func3(c0, c1, c2, c3, c4, c5, c6, c7):
        d = {}
        c0 = chr(c0) ; d[c0] = 1; del d[c0]
        c1 = chr(c1) ; d[c1] = 1; del d[c1]
        c2 = chr(c2) ; d[c2] = 1; del d[c2]
        c3 = chr(c3) ; d[c3] = 1; del d[c3]
        c4 = chr(c4) ; d[c4] = 1; del d[c4]
        c5 = chr(c5) ; d[c5] = 1; del d[c5]
        c6 = chr(c6) ; d[c6] = 1; del d[c6]
        c7 = chr(c7) ; d[c7] = 1; del d[c7]
        return d

    if rdict.STRDICT_INITSIZE != 8: 
        py.test.skip("make dict tests more indepdent from initsize")
    res = interpret(func3, [ord(char_by_hash[i][0]) 
                               for i in range(rdict.STRDICT_INITSIZE)])
    count_frees = 0
    for i in range(len(res.entries)):
        if not res.entries[i].key:
            count_frees += 1
    assert count_frees >= 3

def test_dict_resize():
    def func(want_empty):
        d = {}
        for i in range(rdict.STRDICT_INITSIZE):
            d[chr(ord('a') + i)] = i
        if want_empty:
            for i in range(rdict.STRDICT_INITSIZE):
                del d[chr(ord('a') + i)]
        return d
    res = interpret(func, [0])
    assert len(res.entries) > rdict.STRDICT_INITSIZE 
    res = interpret(func, [1])
    assert len(res.entries) == rdict.STRDICT_INITSIZE 

def test_dict_iteration():
    def func(i, j):
        d = {}
        d['hello'] = i
        d['world'] = j
        k = 1
        for key in d:
            k = k * d[key]
        return k
    res = interpret(func, [6, 7])
    assert res == 42

def test_two_dicts_with_different_value_types():
    def func(i):
        d1 = {}
        d1['hello'] = i + 1
        d2 = {}
        d2['world'] = d1 
        return d2['world']['hello'] 
    res = interpret(func, [5])
    assert res == 6

def test_dict_get():
    def func():
        dic = {}
        x1 = dic.get('hi', 42)
        dic['blah'] = 1 # XXX this triggers type determination
        x2 = dic.get('blah', 2)
        return x1 * 10 + x2
    res = interpret(func, ())
    assert res == 421

def test_dict_get_empty():
    def func():
        # this time without writing to the dict
        dic = {}
        x1 = dic.get('hi', 42)
        x2 = dic.get('blah', 2)
        return x1 * 10 + x2
    res = interpret(func, ())
    assert res == 422

def test_dict_copy():
    def func():
        # XXX this does not work if we use chars, only!
        dic = {'ab':1, 'b':2}
        d2 = dic.copy()
        ok = 1
        for key in d2:
            if dic[key] != d2[key]:
                ok = 0
        ok &= len(dic) == len(d2)
        d2['c'] = 3
        ok &= len(dic) == len(d2) - 1
        return ok
    res = interpret(func, ())
    assert res == 1

def test_dict_update():
    def func():
        dic = {'ab':1000, 'b':200}
        d2 = {'b':30, 'cb':4}
        dic.update(d2)
        ok = len(dic) == 3
        sum = ok
        for key in dic:
            sum += dic[key]
        return sum
    res = interpret(func, ())
    assert res == 1035

def test_dict_keys():
    def func():
        dic = {' 4':1000, ' 8':200}
        keys = dic.keys()
        return ord(keys[0][1]) + ord(keys[1][1]) - 2*ord('0') + len(keys)
    res = interpret(func, ())#, view=True)
    assert res == 14

def test_dict_values():
    def func():
        dic = {' 4':1000, ' 8':200}
        values = dic.values()
        return values[0] + values[1] + len(values)
    res = interpret(func, ())
    assert res == 1202

def test_dict_items():
    def func():
        dic = {' 4':1000, ' 8':200}
        items = dic.items()
        res = len(items)
        for key, value in items:
            res += ord(key[1]) - ord('0') + value
        return res
    res = interpret(func, ())
    assert res == 1214

def test_dict_contains():
    def func():
        dic = {' 4':1000, ' 8':200}
        return ' 4' in dic and ' 9' not in dic
    res = interpret(func, ())
    assert res is True
