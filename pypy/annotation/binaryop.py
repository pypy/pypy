"""
Binary operations between SomeValues.
"""

from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomeObject, SomeInteger, SomeBool
from pypy.annotation.model import SomeString, SomeChar, SomeList, SomeDict
from pypy.annotation.model import SomeTuple, SomeImpossibleValue
from pypy.annotation.model import SomeInstance, SomeBuiltin, SomeIterator
from pypy.annotation.model import SomePBC
from pypy.annotation.model import unionof, set, setunion, missing_operation
from pypy.annotation.factory import generalize
from pypy.annotation.bookkeeper import getbookkeeper
from pypy.annotation.classdef import isclassdef
from pypy.objspace.flow.model import Constant

# convenience only!
def immutablevalue(x):
    return getbookkeeper().immutablevalue(x)

# XXX unify this with ObjSpace.MethodTable
BINARY_OPERATIONS = set(['add', 'sub', 'mul', 'div', 'mod',
                         'and_', 'or_', 'xor',
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
        # XXX assumption: for "X is Y" we for simplification 
        #     assume that X is possibly variable and Y constant 
        #     (and not the other way round) 
        r = SomeBool()
        if obj2.is_constant():
            if obj1.is_constant(): 
                r.const = obj1.const is obj2.const 
        # XXX HACK HACK HACK
        # XXX HACK HACK HACK
        # XXX HACK HACK HACK
        fn, block, i = getbookkeeper().position_key
        annotator = getbookkeeper().annotator
        op = block.operations[i]
        assert op.opname == "is_" 
        assert len(op.args) == 2
        assert annotator.binding(op.args[0]) == obj1 
        r.knowntypedata = (op.args[0], obj2)
        return r

class __extend__(pairtype(SomeInteger, SomeInteger)):
    # unsignedness is considered a rare and contagious disease

    def union((int1, int2)):
        return SomeInteger(nonneg = int1.nonneg and int2.nonneg,
                           unsigned = int1.unsigned or int2.unsigned)

    add = mul = div = mod = or_ = xor = union

    def sub((int1, int2)):
        return SomeInteger(unsigned = int1.unsigned or int2.unsigned)

    def and_((int1, int2)):
        return SomeInteger(nonneg = int1.nonneg or int1.nonneg,
                           unsigned = int1.unsigned or int2.unsigned)


class __extend__(pairtype(SomeBool, SomeBool)):

    def union((boo1, boo2)):
        s = SomeBool() 
        if getattr(boo1, 'const', -1) == getattr(boo2, 'const', -2): 
            s.const = boo1.const 
        if hasattr(boo1, 'knowntypedata') and \
           hasattr(boo2, 'knowntypedata') and \
           boo1.knowntypedata[0] == boo2.knowntypedata[0]: 
            s.knowntypedata = (
                boo1.knowntypedata[0], 
                unionof(boo1.knowntypedata[1], boo2.knowntypedata[1]))
        return s 

class __extend__(pairtype(SomeString, SomeString)):

    def union((str1, str2)):
        return SomeString()

    def add((str1, str2)):
        return SomeString()


class __extend__(pairtype(SomeString, SomeObject)):

    def mod((str, args)):
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
        return SomeDict(setunion(dic1.factories, dic2.factories),
                        unionof(dic1.s_key, dic2.s_key),
                        unionof(dic1.s_value, dic2.s_value))


class __extend__(pairtype(SomeDict, SomeObject)):

    def getitem((dic1, obj2)):
        return dic1.s_value

    def setitem((dic1, obj2), s_value):
        generalize(dic1.factories, obj2, s_value)


class __extend__(pairtype(SomeTuple, SomeInteger)):
    
    def getitem((tup1, int2)):
        if int2.is_constant():
            try:
                return tup1.items[int2.const]
            except IndexError:
                return SomeImpossibleValue()
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
        if basedef is None:
            # print warning?
            return SomeObject()
        return SomeInstance(basedef)

class __extend__(pairtype(SomeIterator, SomeIterator)):

    def union((iter1, iter2)):
        return SomeIterator(unionof(iter1.s_item, iter2.s_item))


class __extend__(pairtype(SomeBuiltin, SomeBuiltin)):

    def union((bltn1, bltn2)):
        if bltn1.analyser != bltn2.analyser:
            assert False, "merging incompatible builtins == BAD!"
            return SomeObject()
        else:
            s_self = unionof(bltn1.s_self, bltn2.s_self)
            return SomeBuiltin(bltn1.analyser, s_self)

class __extend__(pairtype(SomePBC, SomePBC)):
    def union((pbc1, pbc2)):
        if isinstance(pbc1, SomeBuiltin) or isinstance(pbc2, SomeBuiltin):
            assert False, "merging builtin & PBC == BAD!"
        if len(pbc2.prebuiltinstances) > len(pbc1.prebuiltinstances):
            pbc1, pbc2 = pbc2, pbc1
        d = pbc1.prebuiltinstances.copy()
        for x, classdef in pbc2.prebuiltinstances.items():
            if x in d:
                if bool(isclassdef(classdef)) ^ bool(isclassdef(d[x])):
                    raise Exception(
                        "union failed for %r with classdefs %r and %r" % 
                        (x, classdef, d[x]))
                if isclassdef(classdef):
                    classdef = classdef.commonbase(d[x])
            d[x] = classdef
        return SomePBC(d)

class __extend__(pairtype(SomeImpossibleValue, SomeObject)):
    def union((imp1, obj2)):
        return obj2

class __extend__(pairtype(SomeObject, SomeImpossibleValue)):
    def union((obj1, imp2)):
        return obj1

class __extend__(pairtype(SomeInstance, SomePBC)):
    def union((ins, pbc)):
        classdef = ins.classdef.superdef_containing(pbc.knowntype)
        if classdef is None:
            # print warning?
            return SomeObject()
        return SomeInstance(classdef)

class __extend__(pairtype(SomePBC, SomeInstance)):
    def union((pbc, ins)):
        return pair(ins, pbc).union()
