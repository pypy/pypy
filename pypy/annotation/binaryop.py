"""
Binary operations between SomeValues.
"""

from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomeObject, SomeInteger, SomeBool
from pypy.annotation.model import SomeString, SomeChar, SomeList, SomeDict
from pypy.annotation.model import SomeTuple, SomeImpossibleValue
from pypy.annotation.model import SomeInstance, SomeCallable
from pypy.annotation.model import SomeBuiltin, SomeIterator
from pypy.annotation.model import SomePrebuiltConstant, immutablevalue
from pypy.annotation.model import unionof, set, setunion, missing_operation
from pypy.annotation.factory import generalize, isclassdef, getbookkeeper
from pypy.objspace.flow.model import Constant


# XXX unify this with ObjSpace.MethodTable
BINARY_OPERATIONS = set(['add', 'sub', 'mul', 'div', 'mod',
                         'getitem', 'setitem',
                         'inplace_add', 'inplace_sub',
                         'lt', 'le', 'eq', 'ne', 'gt', 'ge', 'is_',
                         'union'])

for opname in BINARY_OPERATIONS:
    missing_operation(pairtype(SomeObject, SomeObject), opname)

#class __extend__(pairtype(SomeFunction, SomeObject)):
#    def union((obj1, obj2)):
#        raise TypeError, "generalizing not allowed: %r AND %r" % (obj1, obj2)
#
#class __extend__(pairtype(SomeObject, SomeFunction)):
#    def union((obj1, obj2)):
#        raise TypeError, "generalizing not allowed: %r AND %r" % (obj2, obj1)

class __extend__(pairtype(SomeObject, SomeObject)):

    def union((obj1, obj2)):
        if obj1 == obj2:
            return obj1
        else:
            #if isinstance(obj1, SomeFunction) or \
            #   isinstance(obj2, SomeFunction): 
            #   raise TypeError, ("generalizing not allowed:"
            #                     "%r AND %r" % (obj1, obj2))
            #    
            result = SomeObject()
            # try to preserve the origin of SomeObjects
            if obj1 == result:
                return obj1
            elif obj2 == result:
                return obj2
            else:
                return result

    def inplace_add((obj1, obj2)):
        return pair(obj1, obj2).add()   # default

    def inplace_sub((obj1, obj2)):
        return pair(obj1, obj2).sub()   # default

    def lt((obj1, obj2)):
        if obj1.is_constant() and obj2.is_constant():
            return immutablevalue(obj1.const < obj2.const)
        else:
            return SomeBool()

    def le((obj1, obj2)):
        if obj1.is_constant() and obj2.is_constant():
            return immutablevalue(obj1.const <= obj2.const)
        else:
            return SomeBool()

    def eq((obj1, obj2)):
        if obj1.is_constant() and obj2.is_constant():
            return immutablevalue(obj1.const == obj2.const)
        else:
            return SomeBool()

    def ne((obj1, obj2)):
        if obj1.is_constant() and obj2.is_constant():
            return immutablevalue(obj1.const != obj2.const)
        else:
            return SomeBool()

    def gt((obj1, obj2)):
        if obj1.is_constant() and obj2.is_constant():
            return immutablevalue(obj1.const > obj2.const)
        else:
            return SomeBool()

    def ge((obj1, obj2)):
        if obj1.is_constant() and obj2.is_constant():
            return immutablevalue(obj1.const >= obj2.const)
        else:
            return SomeBool()

    def is_((obj1, obj2)):
        const = None
        vararg = None
        if obj1.is_constant():
            const = obj1
            var = obj2
            vararg = 1
        if obj2.is_constant():
            if const is not None:
                return immutablevalue(obj1.const is obj2.const)
            # we are in the case "SomeXXX is None" here 
            if obj2.const is None and obj1.__class__ != SomeObject: 
                return immutablevalue(False) 
            const = obj2
            var = obj1
            vararg = 0
        if const is not None:
            # XXX HACK HACK HACK
            # XXX HACK HACK HACK
            # XXX HACK HACK HACK
            # XXX HACK HACK HACK
            # XXX HACK HACK HACK
            fn, block, i = getbookkeeper().position_key
            annotator = getbookkeeper().annotator
            op = block.operations[i]
            assert op.opname == "is_" 
            assert len(op.args) == 2
            assert annotator.binding(op.args[vararg]) is var
            assert annotator.binding(op.args[1-vararg]).const is const.const
            r = SomeBool()
            r.knowntypedata = (op.args[vararg], const)
            return r
            
        return SomeBool()


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


class __extend__(pairtype(SomeList, SomeObject)):

    def inplace_add((lst1, obj2)):
        s_iter = obj2.iter()
        pair(lst1, SomeInteger()).setitem(s_iter.next())
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
            return unionof(*dic1.items.values())

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


class __extend__(pairtype(SomeString, SomeInteger)):

    def getitem((str1, int2)):
        return SomeChar()


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

class __extend__(pairtype(SomeCallable, SomeCallable)):

    def union((cal1, cal2)):
        d = cal1.callables.copy()
        for cal, classdef in cal2.callables.items():
            if cal in d:
                if bool(isclassdef(classdef)) ^ bool(isclassdef(d[cal])):
                    raise Exception(
                        "union failed for %r with classdefs %r and %r" % 
                        (cal, classdef, d[cal]))
                if isclassdef(classdef):
                    classdef = classdef.commonbase(d[cal])
            d[cal] = classdef
        return SomeCallable(d)

class __extend__(pairtype(SomeImpossibleValue, SomeObject)):
    def union((imp1, obj2)):
        return obj2

class __extend__(pairtype(SomeObject, SomeImpossibleValue)):
    def union((obj1, imp2)):
        return obj1


class __extend__(pairtype(SomePrebuiltConstant, SomePrebuiltConstant)):
    def union((pbc1, pbc2)):
        return SomePrebuiltConstant(setunion(pbc1.prebuiltinstances,
                                             pbc2.prebuiltinstances))

class __extend__(pairtype(SomePrebuiltConstant, SomeObject)):
    def getitem((pbc1, obj2)):
        # special case for SomePrebuiltConstants that are dictionaries
        # (actually frozendicts)
        possibleresults = []
        for inst in pbc1.prebuiltinstances:
            if isinstance(inst, dict):
                possibleresults += inst.values()
            #elif isinstance(inst, list):
            #    possibleresults += inst   # maybe
            else:
                raise TypeError, "cannot getitem() from %r" % (inst,)
        possibleresults = [immutablevalue(x) for x in possibleresults]
        return unionof(*possibleresults)
