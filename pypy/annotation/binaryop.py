"""
Binary operations between SomeValues.
"""

from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomeObject, SomeInteger, SomeBool
from pypy.annotation.model import SomeString, SomeList, SomeDict
from pypy.annotation.model import SomeTuple, SomeImpossibleValue
from pypy.annotation.model import SomeInstance, SomeFunction, SomeMethod
from pypy.annotation.model import SomeBuiltin, SomeIterator
from pypy.annotation.model import unionof, set, setunion, missing_operation
from pypy.annotation.factory import generalize


# XXX unify this with ObjSpace.MethodTable
BINARY_OPERATIONS = set(['add', 'sub', 'mul', 'div', 'mod',
                         'getitem', 'setitem',
                         'inplace_add', 'inplace_sub',
                         'lt', 'le', 'eq', 'ne', 'gt', 'ge',
                         'union'])

for opname in BINARY_OPERATIONS:
    missing_operation(pairtype(SomeObject, SomeObject), opname)


class __extend__(pairtype(SomeObject, SomeObject)):

    def union((obj1, obj2)):
        if obj1 == obj2:
            return obj1
        else:
            return SomeObject()

    def inplace_add((obj1, obj2)):
        return pair(obj1, obj2).add()   # default

    def inplace_sub((obj1, obj2)):
        return pair(obj1, obj2).sub()   # default


class __extend__(pairtype(SomeInteger, SomeInteger)):
    # unsignedness is considered a rare and contagious disease

    def union((int1, int2)):
        return SomeInteger(nonneg = int1.nonneg and int2.nonneg,
                           unsigned = int1.unsigned or int2.unsigned)

    def add((int1, int2)):
        return SomeInteger(nonneg = int1.nonneg and int2.nonneg,
                           unsigned = int1.unsigned or int2.unsigned)

    mul = div = mod = add

    def sub((int1, int2)):
        return SomeInteger(unsigned = int1.unsigned or int2.unsigned)

    def lt((int1, int2)): return SomeBool()
    def le((int1, int2)): return SomeBool()
    def eq((int1, int2)): return SomeBool()
    def ne((int1, int2)): return SomeBool()
    def gt((int1, int2)): return SomeBool()
    def ge((int1, int2)): return SomeBool()


class __extend__(pairtype(SomeBool, SomeBool)):

    def union((boo1, boo2)):
        return SomeBool()


class __extend__(pairtype(SomeString, SomeString)):

    def union((str1, str2)):
        return SomeString()

    def add((str1, str2)):
        return SomeString()


class __extend__(pairtype(SomeList, SomeList)):

    def union((lst1, lst2)):
        return SomeList(setunion(lst1.factories, lst2.factories),
                        s_item = unionof(lst1.s_item, lst2.s_item))

    add = union

    def inplace_add((lst1, lst2)):
        pair(lst1, SomeInteger()).setitem(lst2.s_item)
        return lst1


class __extend__(pairtype(SomeTuple, SomeTuple)):

    def union((tup1, tup2)):
        if len(tup1.items) != len(tup2.items):
            return SomeObject()
        else:
            unions = [unionof(x,y) for x,y in zip(tup1.items, tup2.items)]
            return SomeTuple(items = unions)

    def add((tup1, tup2)):
        return SomeTuple(items = tup1.items + tup2.items)


class __extend__(pairtype(SomeDict, SomeDict)):

    def union((dic1, dic2)):
        result = dic1.items.copy()
        for key, s_value in dic2.items.items():
            if key in result:
                result[key] = unionof(result[key], s_value)
            else:
                result[key] = s_value
        return SomeDict(setunion(dic1.factories, dic2.factories), result)


class __extend__(pairtype(SomeDict, SomeObject)):

    def getitem((dic1, obj2)):
        if obj2.is_constant():
            return dic1.items.get(obj2.const, SomeImpossibleValue())
        else:
            return SomeObject()

    def setitem((dic1, obj2), s_value):
        assert obj2.is_constant()
        key = obj2.const
        generalize(dic1.factories, key, s_value)


class __extend__(pairtype(SomeTuple, SomeInteger)):
    
    def getitem((tup1, int2)):
        if int2.is_constant():
            return tup1.items[int2.const]
        else:
            return unionof(*tup1.items)


class __extend__(pairtype(SomeList, SomeInteger)):
    
    def mul((lst1, int2)):
        return lst1

    def getitem((lst1, int2)):
        return lst1.s_item

    def setitem((lst1, int2), s_value):
        generalize(lst1.factories, s_value)


class __extend__(pairtype(SomeInteger, SomeList)):
    
    def mul((int1, lst2)):
        return lst2


class __extend__(pairtype(SomeInstance, SomeInstance)):

    def union((ins1, ins2)):
        basedef = ins1.classdef.commonbase(ins2.classdef)
        return SomeInstance(basedef)


class __extend__(pairtype(SomeIterator, SomeIterator)):

    def union((iter1, iter2)):
        return SomeIterator(unionof(iter1.s_item, iter2.s_item))


class __extend__(pairtype(SomeBuiltin, SomeBuiltin)):

    def union((bltn1, bltn2)):
        if bltn1.analyser != bltn2.analyser:
            return SomeObject()
        else:
            s_self = unionof(bltn1.s_self, bltn2.s_self)
            return SomeBuiltin(bltn1.analyser, s_self)


class __extend__(pairtype(SomeFunction, SomeFunction)):

    def union((fun1, fun2)):
        return SomeFunction(setunion(fun1.funcs, fun2.funcs))


class __extend__(pairtype(SomeMethod, SomeMethod)):

    def union((met1, met2)):
        # the union of the two meths dictionaries is a dictionary
        #   {func: commonbase(met1[func], met2[func])}
        # note that this case is probably very rare
        # (the same Python object found in two different classes)
        d = met1.meths.copy()
        for func, classdef in met2.meths.items():
            if func in d:
                classdef = classdef.commonbase(d[func])
            d[func] = classdef
        return SomeMethod(d)


class __extend__(pairtype(SomeImpossibleValue, SomeObject)):
    def union((imp1, obj2)):
        return obj2

class __extend__(pairtype(SomeObject, SomeImpossibleValue)):
    def union((obj1, imp2)):
        return obj1
