from pypy.translator.translator import TranslationContext
from pypy.rpython.lltypesystem.lltype import *
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.rint import signed_repr
from pypy.rpython.rbool import bool_repr
from pypy.rpython.test.test_llinterp import interpret 
import py

def test_rtuple():
    from pypy.rpython.lltypesystem.rtuple import TupleRepr
    rtuple = TupleRepr(None, [signed_repr, bool_repr])
    assert rtuple.lowleveltype == Ptr(GcStruct('tuple2',
                                               ('item0', Signed),
                                               ('item1', Bool),
                                               ))

# ____________________________________________________________

class AbstractTestRTuple:

    def interpret(self, f, args):
        return interpret(f, args, type_system=self.type_system)

    def test_simple(self):
        def dummyfn(x):
            l = (10,x,30)
            return l[2]
        res = self.interpret(dummyfn,[4])
        assert res == 30

    def test_len(self):
        def dummyfn(x):
            l = (5,x)
            return len(l)
        res = self.interpret(dummyfn, [4])
        assert res == 2

    def test_return_tuple(self):
        def dummyfn(x, y):
            return (x<y, x>y)
        res = self.interpret(dummyfn, [4,5])
        assert res.item0 == True
        assert res.item1 == False

    def test_tuple_concatenation(self):
        def f(n):
            tup = (1,n)
            tup1 = (3,)
            res = tup + tup1 + ()
            return res[0]*100 + res[1]*10 + res[2]
        res = self.interpret(f, [2])
        assert res == 123

    def test_tuple_concatenation_mix(self):
        def f(n):
            tup = (1,n)
            tup1 = ('3',)
            res = tup + tup1
            return res[0]*100 + res[1]*10 + ord(res[2]) - ord('0')
        res = self.interpret(f, [2])
        assert res == 123

    def test_constant_tuple_contains(self): 
        def f(i): 
            t1 = (1, 2, 3, 4)
            return i in t1 
        res = self.interpret(f, [3])
        assert res is True 
        res = self.interpret(f, [0])
        assert res is False 

    def test_constant_tuple_contains2(self):
        def t1():
            return (1,2,3,4)
        def f(i): 
            return i in t1()
        res = self.interpret(f, [3])
        assert res is True 
        res = self.interpret(f, [0])
        assert res is False 

    def test_constant_unichar_tuple_contains(self):
        def f(i):
            return unichr(i) in (u'1', u'9')
        res = self.interpret(f, [49])
        assert res is True 
        res = self.interpret(f, [50])
        assert res is False 

    def test_conv(self):
        if self.type_system == "ootype":
            py.test.skip("fix me if ootypes supports strings")
        def t0():
            return (3, 2, None)
        def t1():
            return (7, 2, "xy")
        def f(i):
            if i == 1:
                return t1()
            else:
                return t0()

        res = self.interpret(f, [1])
        assert res.item0 == 7
        # XXX this assertion will fail once ootypesystem properly supports
        # strings, we're leaving the fix up to that point
        assert isinstance(typeOf(res.item2), Ptr) and ''.join(res.item2.chars) == "xy"
        res = self.interpret(f, [0])
        assert res.item0 == 3
        # XXX see above
        assert isinstance(typeOf(res.item2), Ptr) and not res.item2

    def test_constant_tuples_shared(self):
        def g(n):
            x = (n, 42)    # constant (5, 42) detected by the annotator
            y = (5, 42)    # another one, built by the flow space
            z = x + ()     # yet another
            return id(x) == id(y) == id(z)
        def f():
            return g(5)
        res = self.interpret(f, [])
        assert res is True

    def test_inst_tuple_getitem(self):
        class A:
            pass
        class B(A):
            pass

        def f(i):
            if i:
                x = (1, A())
            else:
                x = (1, B())
            return x[1]
        
        res = self.interpret(f, [0])
        assert self.class_name(res) == "B"
        
    def test_inst_tuple_add_getitem(self):
        class A:
            pass
        class B(A):
            pass

        def f(i):
            x = (1, A())
            y = (2, B())
            if i:
                z = x + y
            else:
                z = y + x
            return z[1]
        
        res = self.interpret(f, [1])
        assert self.class_name(res) == "A"

        res = self.interpret(f, [0])
        assert self.class_name(res) == "B"
        
    def test_type_erase(self):
        class A(object):
            pass
        class B(object):
            pass

        def f():
            return (A(), B()), (B(), A())

        t = TranslationContext()
        s = t.buildannotator().build_types(f, [])
        rtyper = t.buildrtyper(type_system=self.type_system)
        rtyper.specialize()

        s_AB_tup = s.items[0]
        s_BA_tup = s.items[1]
        
        r_AB_tup = rtyper.getrepr(s_AB_tup)
        r_BA_tup = rtyper.getrepr(s_AB_tup)

        assert r_AB_tup.lowleveltype == r_BA_tup.lowleveltype

    def test_tuple_hash(self):
        def f(i, j):
            return hash((i, j))

        res1 = self.interpret(f, [12, 27])
        res2 = self.interpret(f, [27, 12])
        assert res1 != res2

    def test_tuple_to_list(self):
        def f(i, j):
            return list((i, j))

        res = self.interpret(f, [2, 3])
        if self.type_system == "lltype":
            assert res._obj.items == [2, 3]
        else:
            assert res._list == [2, 3]

    def test_tuple_iterator_length1(self):
        def f(i):
            total = 0
            for x in (i,):
                total += x
            return total
        res = self.interpret(f, [93813])
        assert res == 93813

    def test_inst_tuple_iter(self):
        class A:
            pass
        class B(A):
            pass

        def f(i):
            if i:
                x = (A(),)
            else:
                x = (B(),)
            l = None
            for y in x:
                l = y
            return l

        res = self.interpret(f, [0])
        assert self.class_name(res) == "B"

    def test_access_in_try(self):
        def f(sq):
            try:
                return sq[2]
            except ZeroDivisionError:
                return 42
            return -1
        def g(n):
            t = (1,2,n)
            return f(t)
        res = self.interpret(g, [3])
        assert res == 3

class TestLLTuple(AbstractTestRTuple):

    type_system = "lltype"

    def class_name(self, value):
        return "".join(value.super.typeptr.name)[:-1]

class TestOOTuple(AbstractTestRTuple):

    type_system = "ootype"

    def class_name(self, value):
        return ootype.dynamicType(value)._name.split(".")[-1] 

