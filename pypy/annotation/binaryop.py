"""
Binary operations between SomeValues.
"""

from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomeObject, SomeInteger, SomeBool
from pypy.annotation.model import SomeString, SomeList
from pypy.annotation.model import SomeTuple, SomeImpossibleValue
from pypy.annotation.model import SomeInstance, SomeFunction
from pypy.annotation.model import set, setunion, missing_operation
from pypy.annotation.factory import BlockedInference


# XXX unify this with ObjSpace.MethodTable
BINARY_OPERATIONS = set(['add', 'sub', 'mul', 'getitem', 'setitem',
                         'inplace_add',
                         'lt', 'le', 'eq', 'ne', 'gt', 'ge',
                         'union'])

for opname in BINARY_OPERATIONS:
    missing_operation(pairtype(SomeObject, SomeObject), opname)


class __extend__(pairtype(SomeObject, SomeObject)):

    def union((obj1, obj2)):
        return SomeObject()

    def inplace_add((obj1, obj2)):
        return pair(obj1, obj2).add()   # default


class __extend__(pairtype(SomeInteger, SomeInteger)):

    def union((int1, int2)):
        return SomeInteger(nonneg = int1.nonneg and int2.nonneg)

    def add((int1, int2)):
        return SomeInteger(nonneg = int1.nonneg and int2.nonneg)

    mul = add

    def sub((int1, int2)):
        return SomeInteger()

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
                        s_item = pair(lst1.s_item, lst2.s_item).union())

    add = union

    def inplace_add((lst1, lst2)):
        pair(lst1, SomeInteger()).setitem(lst2.s_item)


class __extend__(pairtype(SomeTuple, SomeTuple)):

    def union((tup1, tup2)):
        if len(tup1.items) != len(tup2.items):
            return SomeObject()
        else:
            unions = [pair(x,y).union() for x,y in zip(tup1.items, tup2.items)]
            return SomeTuple(items = unions)

    def add((tup1, tup2)):
        return SomeTuple(items = tup1.items + tup2.items)


class __extend__(pairtype(SomeTuple, SomeInteger)):
    
    def getitem((tup1, int2)):
        if int2.is_constant():
            return tup1.items[int2.const]
        else:
            result = SomeImpossibleValue()
            for a in tup1.items:
                result = pair(result, a).union()
            return result


class __extend__(pairtype(SomeList, SomeInteger)):
    
    def mul((lst1, int2)):
        return lst1

    def getitem((lst1, int2)):
        return lst1.s_item

    def setitem((lst1, int2), s_value):
        if not lst1.s_item.contains(s_value):
            for factory in lst1.factories:
                factory.generalize(s_value)
            raise BlockedInference(lst1.factories)


class __extend__(pairtype(SomeInteger, SomeList)):
    
    def mul((int1, lst2)):
        return lst2


class __extend__(pairtype(SomeInstance, SomeInstance)):

    def union((ins1, ins2)):
        basedef = ins1.classdef.commonbase(ins2.classdef)
        return SomeInstance(basedef)


class __extend__(pairtype(SomeFunction, SomeFunction)):

    def union((fun1, fun2)):
        return SomeFunction(setunion(fun1.funcs, fun2.funcs))


class __extend__(pairtype(SomeImpossibleValue, SomeObject)):
    def union((imp1, obj2)):
        return obj2

class __extend__(pairtype(SomeObject, SomeImpossibleValue)):
    def union((obj1, imp2)):
        return obj1
