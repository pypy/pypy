from pypy.translator.translator import TranslationContext
from pypy.rpython.lltypesystem import lltype 
from pypy.rpython.test.test_llinterp import interpret 
from pypy.rpython import rstr, rint
from pypy.rpython.lltypesystem import rdict

import py
py.log.setconsumer("rtyper", py.log.STDOUT)

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

def test_dict_but_not_with_char_keys():
    def func(i):
        d = {'h': i}
        try:
            return d['hello']
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

def test_dict_clear():
    def func(i):
        d = {'abc': i}
        d['def'] = i+1
        d.clear()
        d['ghi'] = i+2
        return ('abc' not in d and 'def' not in d
                and d['ghi'] == i+2 and len(d) == 1)
    res = interpret(func, [7])
    assert res == True

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
    base = rdict.DICT_INITSIZE
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
        assert not (res.entries[i].everused() and not res.entries[i].valid())

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

    if rdict.DICT_INITSIZE != 8: 
        py.test.skip("make dict tests more indepdent from initsize")
    res = interpret(func3, [ord(char_by_hash[i][0]) 
                               for i in range(rdict.DICT_INITSIZE)])
    count_frees = 0
    for i in range(len(res.entries)):
        if not res.entries[i].everused():
            count_frees += 1
    assert count_frees >= 3

def test_dict_resize():
    def func(want_empty):
        d = {}
        for i in range(rdict.DICT_INITSIZE):
            d[chr(ord('a') + i)] = i
        if want_empty:
            for i in range(rdict.DICT_INITSIZE):
                del d[chr(ord('a') + i)]
        return d
    res = interpret(func, [0])
    assert len(res.entries) > rdict.DICT_INITSIZE 
    res = interpret(func, [1])
    assert len(res.entries) == rdict.DICT_INITSIZE 

def test_dict_valid_resize():
    # see if we find our keys after resize
    def func():
        d = {}
        # fill it up
        for i in range(10):
            d[str(i)] = 0
        # delete again
        for i in range(10):
            del d[str(i)]
        res = 0
    # if it does not crash, we are fine. It crashes if you forget the hash field.
    interpret(func, [])

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

def test_dict_itermethods():
    def func():
        d = {}
        d['hello'] = 6
        d['world'] = 7
        k1 = k2 = k3 = 1
        for key in d.iterkeys():
            k1 = k1 * d[key]
        for value in d.itervalues():
            k2 = k2 * value
        for key, value in d.iteritems():
            assert d[key] == value
            k3 = k3 * value
        return k1 + k2 + k3
    res = interpret(func, [])
    assert res == 42 + 42 + 42

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

def test_dict_setdefault():
    def f():
        d = {}
        d.setdefault('a', 2)
        return d['a']
    res = interpret(f, ())
    assert res == 2

    def f():
        d = {}
        d.setdefault('a', 2)
        x = d.setdefault('a', -3)
        return x
    res = interpret(f, ())
    assert res == 2

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

def test_dict_inst_keys():
    class Empty:
        pass
    class A(Empty):
        pass
    def func():
        dic0 = {Empty(): 2}
        dic = {A(): 1, A(): 2}
        keys = dic.keys()
        return (isinstance(keys[1], A))*2+(isinstance(keys[0],A))
    res = interpret(func, [])
    assert res == 3

def test_dict_inst_iterkeys():
    class Empty:
        pass
    class A(Empty):
        pass
    def func():
        dic0 = {Empty(): 2}
        dic = {A(): 1, A(): 2}
        a = 0
        for k in dic.iterkeys():
            a += isinstance(k, A)
        return a
    res = interpret(func, [])
    assert res == 2

def test_dict_values():
    def func():
        dic = {' 4':1000, ' 8':200}
        values = dic.values()
        return values[0] + values[1] + len(values)
    res = interpret(func, ())
    assert res == 1202

def test_dict_inst_values():
    class A:
        pass
    def func():
        dic = {1: A(), 2: A()}
        vals = dic.values()
        return (isinstance(vals[1], A))*2+(isinstance(vals[0],A))
    res = interpret(func, [])
    assert res == 3

def test_dict_inst_itervalues():
    class A:
        pass
    def func():
        dic = {1: A(), 2: A()}
        a = 0
        for v in dic.itervalues():
            a += isinstance(v, A)
        return a
    res = interpret(func, [])
    assert res == 2

def test_dict_inst_items():
    class Empty:
        pass
    class A:
        pass
    class B(Empty):
        pass
    def func():
        dic0 = {Empty(): 2}
        dic = {B(): A(), B(): A()}
        items = dic.items()
        b = 0
        a = 0
        for k, v in items:
            b += isinstance(k, B)
            a += isinstance(v, A) 
        return 3*b+a
    res = interpret(func, [])
    assert res == 8

def test_dict_inst_iteritems():
    class Empty:
        pass
    class A:
        pass
    class B(Empty):
        pass
    def func():
        dic0 = {Empty(): 2}
        dic = {B(): A(), B(): A()}
        b = 0
        a = 0
        for k, v in dic.iteritems():
            b += isinstance(k, B)
            a += isinstance(v, A) 
        return 3*b+a
    res = interpret(func, [])
    assert res == 8

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

def test_dict_contains_with_constant_dict():
    dic = {'4':1000, ' 8':200}
    def func(i):
        return chr(i) in dic 
    res = interpret(func, [ord('4')]) 
    assert res is True
    res = interpret(func, [1]) 
    assert res is False 

def dict_or_none():
    class A:
        pass
    def negate(d):
        return not d
    def func(n):
        a = A()
        a.d = None
        if n > 0:
            a.d = {str(n): 1, "42": 2}
            del a.d["42"]
        return negate(a.d)
    res = interpret(func, [10])
    assert res is False
    res = interpret(func, [0])
    assert res is True
    res = interpret(func, [42])
    assert res is True

def test_int_dict():
    def func(a, b):
        dic = {12: 34}
        dic[a] = 1000
        return dic.get(b, -123)
    res = interpret(func, [12, 12])
    assert res == 1000
    res = interpret(func, [12, 13])
    assert res == -123
    res = interpret(func, [524, 12])
    assert res == 34
    res = interpret(func, [524, 524])
    assert res == 1000
    res = interpret(func, [524, 1036])
    assert res == -123

# ____________________________________________________________

def not_really_random():
    """A random-ish generator, which also generates nice patterns from time to time.
    Could be useful to detect problems associated with specific usage patterns."""
    import random
    x = random.random()
    print 'random seed: %r' % (x,)
    for i in range(12000):
        r = 3.4 + i/20000.0
        x = r*x - x*x
        assert 0 <= x < 4
        yield x

def test_stress():
    from pypy.annotation.dictdef import DictKey, DictValue
    from pypy.annotation import model as annmodel
    dictrepr = rdict.DictRepr(None, rint.signed_repr, rint.signed_repr,
                              DictKey(None, annmodel.SomeInteger()),
                              DictValue(None, annmodel.SomeInteger()))
    dictrepr.setup()
    l_dict = rdict.ll_newdict(dictrepr.DICT)
    referencetable = [None] * 400
    referencelength = 0
    value = 0

    def complete_check():
        for n, refvalue in zip(range(len(referencetable)), referencetable):
            try:
                gotvalue = rdict.ll_dict_getitem(l_dict, n)
            except KeyError:
                assert refvalue is None
            else:
                assert gotvalue == refvalue

    for x in not_really_random():
        n = int(x*100.0)    # 0 <= x < 400
        op = repr(x)[-1]
        if op <= '2' and referencetable[n] is not None:
            rdict.ll_dict_delitem(l_dict, n)
            referencetable[n] = None
            referencelength -= 1
        elif op <= '6':
            rdict.ll_dict_setitem(l_dict, n, value)
            if referencetable[n] is None:
                referencelength += 1
            referencetable[n] = value
            value += 1
        else:
            try:
                gotvalue = rdict.ll_dict_getitem(l_dict, n)
            except KeyError:
                assert referencetable[n] is None
            else:
                assert gotvalue == referencetable[n]
        if 1.38 <= x <= 1.39:
            complete_check()
            print 'current dict length:', referencelength
        assert l_dict.num_items == referencelength
    complete_check()

# ____________________________________________________________

def test_opt_nullkeymarker():
    def f():
        d = {"hello": None}
        d["world"] = None
        return "hello" in d, d
    res = interpret(f, [])
    assert res.item0 == True
    DICT = lltype.typeOf(res.item1).TO
    assert not hasattr(DICT.entries.TO.OF, 'f_everused')# non-None string keys
    assert not hasattr(DICT.entries.TO.OF, 'f_valid')   # strings have a dummy

def test_opt_nullvaluemarker():
    def f(n):
        d = {-5: "abcd"}
        d[123] = "def"
        return len(d[n]), d
    res = interpret(f, [-5])
    assert res.item0 == 4
    DICT = lltype.typeOf(res.item1).TO
    assert not hasattr(DICT.entries.TO.OF, 'f_everused')# non-None str values
    assert not hasattr(DICT.entries.TO.OF, 'f_valid')   # strs have a dummy

def test_opt_nonullmarker():
    class A:
        pass
    def f(n):
        if n > 5:
            a = A()
        else:
            a = None
        d = {a: -5441}
        d[A()] = n+9872
        return d[a], d
    res = interpret(f, [-5])
    assert res.item0 == -5441
    DICT = lltype.typeOf(res.item1).TO
    assert hasattr(DICT.entries.TO.OF, 'f_everused') # can-be-None A instances
    assert not hasattr(DICT.entries.TO.OF, 'f_valid')# with a dummy A instance

    res = interpret(f, [6])
    assert res.item0 == -5441

def test_opt_nonnegint_dummy():
    def f(n):
        d = {n: 12}
        d[-87] = 24
        del d[n]
        return len(d.copy()), d[-87], d
    res = interpret(f, [5])
    assert res.item0 == 1
    assert res.item1 == 24
    DICT = lltype.typeOf(res.item2).TO
    assert hasattr(DICT.entries.TO.OF, 'f_everused') # all ints can be zero
    assert not hasattr(DICT.entries.TO.OF, 'f_valid')# nonneg int: dummy -1

def test_opt_no_dummy():
    def f(n):
        d = {n: 12}
        d[-87] = -24
        del d[n]
        return len(d.copy()), d[-87], d
    res = interpret(f, [5])
    assert res.item0 == 1
    assert res.item1 == -24
    DICT = lltype.typeOf(res.item2).TO
    assert hasattr(DICT.entries.TO.OF, 'f_everused') # all ints can be zero
    assert hasattr(DICT.entries.TO.OF, 'f_valid')    # no dummy available

def test_opt_multiple_identical_dicts():
    def f(n):
        s = "x" * n
        d1 = {s: 12}
        d2 = {s: 24}
        d3 = {s: 36}
        d1["a"] = d2[s]   # 24
        d3[s] += d1["a"]  # 60
        d2["bc"] = d3[s]  # 60
        return d2["bc"], d1, d2, d3
    res = interpret(f, [5])
    assert res.item0 == 60
    # all three dicts should use the same low-level type
    assert lltype.typeOf(res.item1) == lltype.typeOf(res.item2)
    assert lltype.typeOf(res.item1) == lltype.typeOf(res.item3)

# ____________________________________________________________

def test_id_instances_keys():
    class A:
        pass
    class B(A):
        pass
    def f():
        a = A()
        b = B()
        d = {}
        d[b] = 7
        d[a] = 3
        return len(d) + d[a] + d[b]
    res = interpret(f, [])
    assert res == 12

def test_captured_get():
    get = {1:2}.get
    def f():
        return get(1, 3)+get(2, 4)
    res = interpret(f, [])
    assert res == 6

    def g(h):
        return h(1, 3)
    def f():
        return g(get)

    res = interpret(f, [])
    assert res == 2    

def test_specific_obscure_bug():
    class A: pass
    class B: pass   # unrelated kinds of instances
    def f():
        lst = [A()]
        res1 = A() in lst
        d2 = {B(): None, B(): None}
        return res1+len(d2)
    res = interpret(f, [])
    assert res == 2


def test_type_erase():
    class A(object):
        pass
    class B(object):
        pass

    def f():
        return {A(): B()}, {B(): A()}

    t = TranslationContext()
    s = t.buildannotator().build_types(f, [])
    rtyper = t.buildrtyper()
    rtyper.specialize()

    s_AB_dic = s.items[0]
    s_BA_dic = s.items[1]
    
    r_AB_dic = rtyper.getrepr(s_AB_dic)
    r_BA_dic = rtyper.getrepr(s_AB_dic)

    assert r_AB_dic.lowleveltype == r_BA_dic.lowleveltype

def test_tuple_dict():
    def f(i):
        d = {}
        d[(1, 2)] = 4
        d[(1, 3)] = 6
        return d[(1, i)]

    res = interpret(f, [2])
    assert res == f(2)
        
def test_dict_of_dict():
    def f(n):
        d = {}
        d[5] = d
        d[6] = {}
        return len(d[n])

    res = interpret(f, [5])
    assert res == 2
    res = interpret(f, [6])
    assert res == 0

def test_access_in_try():
    def f(d):
        try:
            return d[2]
        except ZeroDivisionError:
            return 42
        return -1
    def g(n):
        d = {1: n, 2: 2*n}
        return f(d)
    res = interpret(g, [3])
    assert res == 6

def test_access_in_try_set():
    def f(d):
        try:
            d[2] = 77
        except ZeroDivisionError:
            return 42
        return -1
    def g(n):
        d = {1: n}
        f(d)
        return d[2]
    res = interpret(g, [3])
    assert res == 77
