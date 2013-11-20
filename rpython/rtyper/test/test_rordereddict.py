
import py
try:
    from collections import OrderedDict
except ImportError:     # Python 2.6
    py.test.skip("requires collections.OrderedDict")
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.lltypesystem import rordereddict, rstr
from rpython.rlib.rarithmetic import intmask
from rpython.rtyper.annlowlevel import llstr, hlstr
from rpython.rtyper.test.test_rdict import BaseTestRDict
from rpython.rlib import objectmodel


def get_indexes(ll_d):
    return ll_d.indexes._obj.container._as_ptr()

def foreach_index(ll_d):
    indexes = get_indexes(ll_d)
    for i in range(len(indexes)):
        yield rffi.cast(lltype.Signed, indexes[i])

def count_items(ll_d, ITEM):
    c = 0
    for item in foreach_index(ll_d):
        if item == ITEM:
            c += 1
    return c


class TestRDictDirect(object):
    dummykeyobj = None
    dummyvalueobj = None

    def _get_str_dict(self):
        # STR -> lltype.Signed
        DICT = rordereddict.get_ll_dict(lltype.Ptr(rstr.STR), lltype.Signed,
                                 ll_fasthash_function=rstr.LLHelpers.ll_strhash,
                                 ll_hash_function=rstr.LLHelpers.ll_strhash,
                                 ll_eq_function=rstr.LLHelpers.ll_streq,
                                 dummykeyobj=self.dummykeyobj,
                                 dummyvalueobj=self.dummyvalueobj)
        return DICT

    def test_dict_creation(self):
        DICT = self._get_str_dict()
        ll_d = rordereddict.ll_newdict(DICT)
        lls = llstr("abc")
        rordereddict.ll_dict_setitem(ll_d, lls, 13)
        assert count_items(ll_d, rordereddict.FREE) == rordereddict.DICT_INITSIZE - 1
        assert rordereddict.ll_dict_getitem(ll_d, llstr("abc")) == 13
        assert rordereddict.ll_dict_getitem(ll_d, lls) == 13
        rordereddict.ll_dict_setitem(ll_d, lls, 42)
        assert rordereddict.ll_dict_getitem(ll_d, lls) == 42
        rordereddict.ll_dict_setitem(ll_d, llstr("abc"), 43)
        assert rordereddict.ll_dict_getitem(ll_d, lls) == 43

    def test_dict_creation_2(self):
        DICT = self._get_str_dict()
        ll_d = rordereddict.ll_newdict(DICT)
        llab = llstr("ab")
        llb = llstr("b")
        rordereddict.ll_dict_setitem(ll_d, llab, 1)
        rordereddict.ll_dict_setitem(ll_d, llb, 2)
        assert rordereddict.ll_dict_getitem(ll_d, llb) == 2

    def test_dict_store_get(self):
        DICT = self._get_str_dict()
        ll_d = rordereddict.ll_newdict(DICT)
        for i in range(20):
            for j in range(i):
                assert rordereddict.ll_dict_getitem(ll_d, llstr(str(j))) == j
            rordereddict.ll_dict_setitem(ll_d, llstr(str(i)), i)
        assert ll_d.num_items == 20
        for i in range(20):
            assert rordereddict.ll_dict_getitem(ll_d, llstr(str(i))) == i

    def test_dict_store_get_del(self):
        DICT = self._get_str_dict()
        ll_d = rordereddict.ll_newdict(DICT)
        for i in range(20):
            for j in range(0, i, 2):
                assert rordereddict.ll_dict_getitem(ll_d, llstr(str(j))) == j
            rordereddict.ll_dict_setitem(ll_d, llstr(str(i)), i)
            if i % 2 != 0:
                rordereddict.ll_dict_delitem(ll_d, llstr(str(i)))
        assert ll_d.num_items == 10
        for i in range(0, 20, 2):
            assert rordereddict.ll_dict_getitem(ll_d, llstr(str(i))) == i

    def test_dict_del_lastitem(self):
        DICT = self._get_str_dict()
        ll_d = rordereddict.ll_newdict(DICT)
        py.test.raises(KeyError, rordereddict.ll_dict_delitem, ll_d, llstr("abc"))
        rordereddict.ll_dict_setitem(ll_d, llstr("abc"), 13)
        py.test.raises(KeyError, rordereddict.ll_dict_delitem, ll_d, llstr("def"))
        rordereddict.ll_dict_delitem(ll_d, llstr("abc"))
        assert count_items(ll_d, rordereddict.FREE) == rordereddict.DICT_INITSIZE - 1
        assert count_items(ll_d, rordereddict.DELETED) == 1
        py.test.raises(KeyError, rordereddict.ll_dict_getitem, ll_d, llstr("abc"))

    def test_dict_del_not_lastitem(self):
        DICT = self._get_str_dict()
        ll_d = rordereddict.ll_newdict(DICT)
        rordereddict.ll_dict_setitem(ll_d, llstr("abc"), 13)
        rordereddict.ll_dict_setitem(ll_d, llstr("def"), 15)
        rordereddict.ll_dict_delitem(ll_d, llstr("abc"))
        assert count_items(ll_d, rordereddict.FREE) == rordereddict.DICT_INITSIZE - 2
        assert count_items(ll_d, rordereddict.DELETED) == 1

    def test_dict_resize(self):
        DICT = self._get_str_dict()
        ll_d = rordereddict.ll_newdict(DICT)
        rordereddict.ll_dict_setitem(ll_d, llstr("a"), 1)
        rordereddict.ll_dict_setitem(ll_d, llstr("b"), 2)
        rordereddict.ll_dict_setitem(ll_d, llstr("c"), 3)
        rordereddict.ll_dict_setitem(ll_d, llstr("d"), 4)
        assert len(get_indexes(ll_d)) == 8
        rordereddict.ll_dict_setitem(ll_d, llstr("e"), 5)
        rordereddict.ll_dict_setitem(ll_d, llstr("f"), 6)
        assert len(get_indexes(ll_d)) == 32
        for item in ['a', 'b', 'c', 'd', 'e', 'f']:
            assert rordereddict.ll_dict_getitem(ll_d, llstr(item)) == ord(item) - ord('a') + 1

    def test_dict_grow_cleanup(self):
        DICT = self._get_str_dict()
        ll_d = rordereddict.ll_newdict(DICT)
        lls = llstr("a")
        for i in range(40):
            rordereddict.ll_dict_setitem(ll_d, lls, i)
            rordereddict.ll_dict_delitem(ll_d, lls)
        assert ll_d.num_used_items <= 10

    def test_dict_iteration(self):
        DICT = self._get_str_dict()
        ll_d = rordereddict.ll_newdict(DICT)
        rordereddict.ll_dict_setitem(ll_d, llstr("k"), 1)
        rordereddict.ll_dict_setitem(ll_d, llstr("j"), 2)
        ITER = rordereddict.get_ll_dictiter(lltype.Ptr(DICT))
        ll_iter = rordereddict.ll_dictiter(ITER, ll_d)
        ll_iterkeys = rordereddict.ll_dictnext_group['keys']
        next = ll_iterkeys(lltype.Signed, ll_iter)
        assert hlstr(next) == "k"
        next = ll_iterkeys(lltype.Signed, ll_iter)
        assert hlstr(next) == "j"
        py.test.raises(StopIteration, ll_iterkeys, lltype.Signed, ll_iter)

    def test_popitem(self):
        DICT = self._get_str_dict()
        ll_d = rordereddict.ll_newdict(DICT)
        rordereddict.ll_dict_setitem(ll_d, llstr("k"), 1)
        rordereddict.ll_dict_setitem(ll_d, llstr("j"), 2)
        TUP = lltype.Ptr(lltype.GcStruct('x', ('item0', lltype.Ptr(rstr.STR)),
                                              ('item1', lltype.Signed)))
        ll_elem = rordereddict.ll_dict_popitem(TUP, ll_d)
        assert hlstr(ll_elem.item0) == "j"
        assert ll_elem.item1 == 2
        ll_elem = rordereddict.ll_dict_popitem(TUP, ll_d)
        assert hlstr(ll_elem.item0) == "k"
        assert ll_elem.item1 == 1
        py.test.raises(KeyError, rordereddict.ll_dict_popitem, TUP, ll_d)

    def test_direct_enter_and_del(self):
        def eq(a, b):
            return a == b

        DICT = rordereddict.get_ll_dict(lltype.Signed, lltype.Signed,
                                 ll_fasthash_function=intmask,
                                 ll_hash_function=intmask,
                                 ll_eq_function=eq)
        ll_d = rordereddict.ll_newdict(DICT)
        numbers = [i * rordereddict.DICT_INITSIZE + 1 for i in range(8)]
        for num in numbers:
            rordereddict.ll_dict_setitem(ll_d, num, 1)
            rordereddict.ll_dict_delitem(ll_d, num)
            for k in foreach_index(ll_d):
                assert k < rordereddict.VALID_OFFSET

    def test_contains(self):
        DICT = self._get_str_dict()
        ll_d = rordereddict.ll_newdict(DICT)
        rordereddict.ll_dict_setitem(ll_d, llstr("k"), 1)
        assert rordereddict.ll_dict_contains(ll_d, llstr("k"))
        assert not rordereddict.ll_dict_contains(ll_d, llstr("j"))

    def test_clear(self):
        DICT = self._get_str_dict()
        ll_d = rordereddict.ll_newdict(DICT)
        rordereddict.ll_dict_setitem(ll_d, llstr("k"), 1)
        rordereddict.ll_dict_setitem(ll_d, llstr("j"), 1)
        rordereddict.ll_dict_setitem(ll_d, llstr("l"), 1)
        rordereddict.ll_dict_clear(ll_d)
        assert ll_d.num_items == 0

    def test_get(self):
        DICT = self._get_str_dict()
        ll_d = rordereddict.ll_newdict(DICT)
        rordereddict.ll_dict_setitem(ll_d, llstr("k"), 1)
        assert rordereddict.ll_dict_get(ll_d, llstr("k"), 32) == 1
        assert rordereddict.ll_dict_get(ll_d, llstr("j"), 32) == 32

    def test_setdefault(self):
        DICT = self._get_str_dict()
        ll_d = rordereddict.ll_newdict(DICT)
        rordereddict.ll_dict_setitem(ll_d, llstr("k"), 1)
        assert rordereddict.ll_dict_setdefault(ll_d, llstr("j"), 42) == 42
        assert rordereddict.ll_dict_getitem(ll_d, llstr("j")) == 42
        assert rordereddict.ll_dict_setdefault(ll_d, llstr("k"), 42) == 1
        assert rordereddict.ll_dict_getitem(ll_d, llstr("k")) == 1

    def test_copy(self):
        DICT = self._get_str_dict()
        ll_d = rordereddict.ll_newdict(DICT)
        rordereddict.ll_dict_setitem(ll_d, llstr("k"), 1)
        rordereddict.ll_dict_setitem(ll_d, llstr("j"), 2)
        ll_d2 = rordereddict.ll_dict_copy(ll_d)
        for ll_d3 in [ll_d, ll_d2]:
            assert rordereddict.ll_dict_getitem(ll_d3, llstr("k")) == 1
            assert rordereddict.ll_dict_get(ll_d3, llstr("j"), 42) == 2
            assert rordereddict.ll_dict_get(ll_d3, llstr("i"), 42) == 42

    def test_update(self):
        DICT = self._get_str_dict()
        ll_d1 = rordereddict.ll_newdict(DICT)
        ll_d2 = rordereddict.ll_newdict(DICT)
        rordereddict.ll_dict_setitem(ll_d1, llstr("k"), 5)
        rordereddict.ll_dict_setitem(ll_d1, llstr("j"), 6)
        rordereddict.ll_dict_setitem(ll_d2, llstr("i"), 7)
        rordereddict.ll_dict_setitem(ll_d2, llstr("k"), 8)
        rordereddict.ll_dict_update(ll_d1, ll_d2)
        for key, value in [("k", 8), ("i", 7), ("j", 6)]:
            assert rordereddict.ll_dict_getitem(ll_d1, llstr(key)) == value

    def test_pop(self):
        DICT = self._get_str_dict()
        ll_d = rordereddict.ll_newdict(DICT)
        rordereddict.ll_dict_setitem(ll_d, llstr("k"), 5)
        rordereddict.ll_dict_setitem(ll_d, llstr("j"), 6)
        assert rordereddict.ll_dict_pop(ll_d, llstr("k")) == 5
        assert rordereddict.ll_dict_pop(ll_d, llstr("j")) == 6
        py.test.raises(KeyError, rordereddict.ll_dict_pop, ll_d, llstr("k"))
        py.test.raises(KeyError, rordereddict.ll_dict_pop, ll_d, llstr("j"))

    def test_pop_default(self):
        DICT = self._get_str_dict()
        ll_d = rordereddict.ll_newdict(DICT)
        rordereddict.ll_dict_setitem(ll_d, llstr("k"), 5)
        rordereddict.ll_dict_setitem(ll_d, llstr("j"), 6)
        assert rordereddict.ll_dict_pop_default(ll_d, llstr("k"), 42) == 5
        assert rordereddict.ll_dict_pop_default(ll_d, llstr("j"), 41) == 6
        assert rordereddict.ll_dict_pop_default(ll_d, llstr("k"), 40) == 40
        assert rordereddict.ll_dict_pop_default(ll_d, llstr("j"), 39) == 39

class TestRDictDirectDummyKey(TestRDictDirect):
    class dummykeyobj:
        ll_dummy_value = llstr("dupa")

class TestRDictDirectDummyValue(TestRDictDirect):
    class dummyvalueobj:
        ll_dummy_value = -42

class TestOrderedRDict(BaseTestRDict):
    @staticmethod
    def newdict():
        return OrderedDict()

    @staticmethod
    def newdict2():
        return OrderedDict()

    def test_two_dicts_with_different_value_types(self):
        def func(i):
            d1 = OrderedDict()
            d1['hello'] = i + 1
            d2 = OrderedDict()
            d2['world'] = d1
            return d2['world']['hello']
        res = self.interpret(func, [5])
        assert res == 6

    def test_dict_with_SHORT_keys(self):
        py.test.skip("I don't want to edit this file on two branches")

    def test_memoryerror_should_not_insert(self):
        py.test.skip("I don't want to edit this file on two branches")


    def test_r_dict(self):
        class FooError(Exception):
            pass
        def myeq(n, m):
            return n == m
        def myhash(n):
            if n < 0:
                raise FooError
            return -n
        def f(n):
            d = objectmodel.r_ordereddict(myeq, myhash)
            for i in range(10):
                d[i] = i*i
            try:
                value1 = d[n]
            except FooError:
                value1 = 99
            try:
                value2 = n in d
            except FooError:
                value2 = 99
            try:
                value3 = d[-n]
            except FooError:
                value3 = 99
            try:
                value4 = (-n) in d
            except FooError:
                value4 = 99
            return (value1 * 1000000 +
                    value2 * 10000 +
                    value3 * 100 +
                    value4)
        res = self.interpret(f, [5])
        assert res == 25019999

    def test_dict_popitem_hash(self):
        def deq(n, m):
            return n == m
        def dhash(n):
            return ~n
        def func():
            d = objectmodel.r_ordereddict(deq, dhash)
            d[5] = 2
            d[6] = 3
            k1, v1 = d.popitem()
            assert len(d) == 1
            k2, v2 = d.popitem()
            try:
                d.popitem()
            except KeyError:
                pass
            else:
                assert 0, "should have raised KeyError"
            assert len(d) == 0
            return k1*1000 + v1*100 + k2*10 + v2

        res = self.interpret(func, [])
        assert res in [5263, 6352]
