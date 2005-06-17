"""
Binary operations between SomeValues.
"""

import operator
from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomeObject, SomeInteger, SomeBool
from pypy.annotation.model import SomeString, SomeChar, SomeList, SomeDict
from pypy.annotation.model import SomeUnicodeCodePoint
from pypy.annotation.model import SomeTuple, SomeImpossibleValue
from pypy.annotation.model import SomeInstance, SomeBuiltin, SomeIterator
from pypy.annotation.model import SomePBC, SomeSlice, SomeFloat
from pypy.annotation.model import unionof, UnionError, set, missing_operation, TLS
from pypy.annotation.model import add_knowntypedata, merge_knowntypedata
from pypy.annotation.bookkeeper import getbookkeeper
from pypy.annotation.classdef import isclassdef
from pypy.objspace.flow.model import Constant, Variable

# convenience only!
def immutablevalue(x):
    return getbookkeeper().immutablevalue(x)

# XXX unify this with ObjSpace.MethodTable
BINARY_OPERATIONS = set(['add', 'sub', 'mul', 'div', 'mod',
                         'truediv', 'floordiv', 'divmod', 'pow',
                         'and_', 'or_', 'xor',
                         'lshift', 'rshift',
                         'getitem', 'setitem', 'delitem',
                         'inplace_add', 'inplace_sub', 'inplace_mul',
                         'inplace_truediv', 'inplace_floordiv', 'inplace_div',
                         'inplace_mod', 'inplace_pow',
                         'inplace_lshift', 'inplace_rshift',
                         'inplace_and', 'inplace_or', 'inplace_xor',
                         'lt', 'le', 'eq', 'ne', 'gt', 'ge', 'is_', 'cmp',
                         'coerce',
                         ]
                        +[opname+'_ovf' for opname in
                          """add sub mul floordiv div mod pow lshift
                           """.split()
                          ])

for opname in BINARY_OPERATIONS:
    missing_operation(pairtype(SomeObject, SomeObject), opname)

class __extend__(pairtype(SomeObject, SomeObject)):

    def union((obj1, obj2)):
        if obj1 == obj2:
            return obj1
        else:
            result = SomeObject()
            if obj1.knowntype == obj2.knowntype and obj1.knowntype != object:
                result.knowntype = obj1.knowntype
            is_type_of1 = getattr(obj1, 'is_type_of', None)
            is_type_of2 = getattr(obj2, 'is_type_of', None)
            if obj1.is_constant() and obj2.is_constant() and obj1.const == obj2.const:
                result.const = obj1.const
                is_type_of = {}
                if is_type_of1:
                    for v in is_type_of1:
                        is_type_of[v] = True
                if is_type_of2:
                    for v in is_type_of2:
                        is_type_of[v] = True
                if is_type_of:
                    result.is_type_of = is_type_of.keys()
            else:
                if is_type_of1 and is_type_of1 == is_type_of2:
                    result.is_type_of = is_type_of1
            # try to preserve the origin of SomeObjects
            if obj1 == result:
                return obj1
            elif obj2 == result:
                return obj2
            else:
                return result

    # inplace_xxx ---> xxx by default
    def inplace_add((obj1, obj2)):      return pair(obj1, obj2).add()
    def inplace_sub((obj1, obj2)):      return pair(obj1, obj2).sub()
    def inplace_mul((obj1, obj2)):      return pair(obj1, obj2).mul()
    def inplace_truediv((obj1, obj2)):  return pair(obj1, obj2).truediv()
    def inplace_floordiv((obj1, obj2)): return pair(obj1, obj2).floordiv()
    def inplace_div((obj1, obj2)):      return pair(obj1, obj2).div()
    def inplace_mod((obj1, obj2)):      return pair(obj1, obj2).mod()
    def inplace_pow((obj1, obj2)):      return pair(obj1, obj2).pow(
                                                      SomePBC({None: True}))
    def inplace_lshift((obj1, obj2)):   return pair(obj1, obj2).lshift()
    def inplace_rshift((obj1, obj2)):   return pair(obj1, obj2).rshift()
    def inplace_and((obj1, obj2)):      return pair(obj1, obj2).and_()
    def inplace_or((obj1, obj2)):       return pair(obj1, obj2).or_()
    def inplace_xor((obj1, obj2)):      return pair(obj1, obj2).xor()

    def lt((obj1, obj2)):
        if obj1.is_constant() and obj2.is_constant():
            return immutablevalue(obj1.const < obj2.const)
        else:
            getbookkeeper().count("non_int_comp", obj1, obj2)
            return SomeBool()

    def le((obj1, obj2)):
        if obj1.is_constant() and obj2.is_constant():
            return immutablevalue(obj1.const <= obj2.const)
        else:
            getbookkeeper().count("non_int_comp", obj1, obj2)
            return SomeBool()

    def eq((obj1, obj2)):
        if obj1.is_constant() and obj2.is_constant():
            return immutablevalue(obj1.const == obj2.const)
        else:
            getbookkeeper().count("non_int_eq", obj1, obj2)
            return SomeBool()

    def ne((obj1, obj2)):
        if obj1.is_constant() and obj2.is_constant():
            return immutablevalue(obj1.const != obj2.const)
        else:
            getbookkeeper().count("non_int_eq", obj1, obj2)
            return SomeBool()

    def gt((obj1, obj2)):
        if obj1.is_constant() and obj2.is_constant():
            return immutablevalue(obj1.const > obj2.const)
        else:
            getbookkeeper().count("non_int_comp", obj1, obj2)
            return SomeBool()

    def ge((obj1, obj2)):
        if obj1.is_constant() and obj2.is_constant():
            return immutablevalue(obj1.const >= obj2.const)
        else:
            getbookkeeper().count("non_int_comp", obj1, obj2)
            return SomeBool()

    def cmp((obj1, obj2)):
        if obj1.is_constant() and obj2.is_constant():
            return immutablevalue(cmp(obj1.const, obj2.const))
        else:
            getbookkeeper().count("non_int_comp", obj1, obj2)
            return SomeInteger()

    def is_((obj1, obj2)):
        r = SomeBool()
        if obj2.is_constant():
            if obj1.is_constant(): 
                r.const = obj1.const is obj2.const
            if obj2.const is None and not obj1.can_be_none():
                r.const = False
        elif obj1.is_constant():
            if obj1.const is None and not obj2.can_be_none():
                r.const = False
        # XXX HACK HACK HACK
        # XXX HACK HACK HACK
        # XXX HACK HACK HACK
        bk = getbookkeeper()
        if bk is not None: # for testing
            knowntypedata = r.knowntypedata = {}
            fn, block, i = bk.position_key

            annotator = bk.annotator
            op = block.operations[i]
            assert op.opname == "is_" 
            assert len(op.args) == 2                

            def bind(src_obj, tgt_obj, tgt_arg):
                if hasattr(tgt_obj, 'is_type_of') and src_obj.is_constant():
                    add_knowntypedata(knowntypedata, True, tgt_obj.is_type_of, 
                                      bk.valueoftype(src_obj.const))

                assert annotator.binding(op.args[tgt_arg]) == tgt_obj
                add_knowntypedata(knowntypedata, True, [op.args[tgt_arg]], src_obj)

                nonnone_obj = tgt_obj
                if src_obj.is_constant() and src_obj.const is None and tgt_obj.can_be_none():
                    nonnone_obj = tgt_obj.nonnoneify()

                add_knowntypedata(knowntypedata, False, [op.args[tgt_arg]], nonnone_obj)

            bind(obj2, obj1, 0)
            bind(obj1, obj2, 1)
                
        return r

    def divmod((obj1, obj2)):
        return SomeTuple([pair(obj1, obj2).div(), pair(obj1, obj2).mod()])

    def coerce((obj1, obj2)):
        return pair(obj1, obj2).union()   # reasonable enough

# cloning a function with identical code, for the can_only_throw attribute
def _clone(f, can_only_throw = None):
    newfunc = type(f)(f.func_code, f.func_globals, f.func_name,
                      f.func_defaults, f.func_closure)
    if can_only_throw is not None:
        newfunc.can_only_throw = can_only_throw
    return newfunc

class __extend__(pairtype(SomeInteger, SomeInteger)):
    # unsignedness is considered a rare and contagious disease

    def union((int1, int2)):
        unsigned = int1.unsigned or int2.unsigned
        return SomeInteger(nonneg = unsigned or (int1.nonneg and int2.nonneg),
                           unsigned=unsigned)

    or_ = xor = add = mul = _clone(union, [])
    add_ovf = mul_ovf = _clone(union, [OverflowError])
    div = floordiv = mod = _clone(union, [ZeroDivisionError])
    div_ovf= floordiv_ovf = mod_ovf = _clone(union, [ZeroDivisionError, OverflowError])

    def truediv((int1, int2)):
        return SomeFloat()
    truediv.can_only_throw = [ZeroDivisionError]
    truediv_ovf = _clone(truediv, [ZeroDivisionError, OverflowError])

    def sub((int1, int2)):
        return SomeInteger(unsigned = int1.unsigned or int2.unsigned)
    sub.can_only_throw = []
    sub_ovf = _clone(sub, [OverflowError])

    def and_((int1, int2)):
        unsigned = int1.unsigned or int2.unsigned
        return SomeInteger(nonneg = unsigned or int1.nonneg or int2.nonneg,
                           unsigned = unsigned)
    and_.can_only_throw = []

    def lshift((int1, int2)):
        if int1.unsigned:
            return SomeInteger(unsigned=True)
        return SomeInteger()
    lshift.can_only_throw = [ValueError]
    rshift = lshift
    lshift_ovf = _clone(lshift, [ValueError, OverflowError])

    def pow((int1, int2), obj3):
        if int1.unsigned or int2.unsigned or getattr(obj3, 'unsigned', False):
            return SomeInteger(unsigned=True)
        return SomeInteger()
    pow.can_only_throw = [ZeroDivisionError]
    pow_ovf = _clone(pow, [ZeroDivisionError, OverflowError])

    def _compare_helper((int1, int2), opname, operation):
        if int1.is_constant() and int2.is_constant():
            r = immutablevalue(operation(int1.const, int2.const))
        else:
            r = SomeBool()
        knowntypedata = {}
        # XXX HACK HACK HACK
        # propagate nonneg information between the two arguments
        fn, block, i = getbookkeeper().position_key
        op = block.operations[i]
        assert op.opname == opname
        assert len(op.args) == 2
        if int1.nonneg and isinstance(op.args[1], Variable):
            case = opname in ('lt', 'le', 'eq')
            add_knowntypedata(knowntypedata, case, [op.args[1]],
                              SomeInteger(nonneg=True))
        if int2.nonneg and isinstance(op.args[0], Variable):
            case = opname in ('gt', 'ge', 'eq')
            add_knowntypedata(knowntypedata, case, [op.args[0]],
                              SomeInteger(nonneg=True))
        if knowntypedata:
            r.knowntypedata = knowntypedata
        return r

    def lt(intint): return intint._compare_helper('lt', operator.lt)
    def le(intint): return intint._compare_helper('le', operator.le)
    def eq(intint): return intint._compare_helper('eq', operator.eq)
    def ne(intint): return intint._compare_helper('ne', operator.ne)
    def gt(intint): return intint._compare_helper('gt', operator.gt)
    def ge(intint): return intint._compare_helper('ge', operator.ge)


class __extend__(pairtype(SomeBool, SomeBool)):

    def union((boo1, boo2)):
        s = SomeBool() 
        if getattr(boo1, 'const', -1) == getattr(boo2, 'const', -2): 
            s.const = boo1.const 
        if hasattr(boo1, 'knowntypedata') and \
           hasattr(boo2, 'knowntypedata'):
            ktd = merge_knowntypedata(boo1.knowntypedata, boo2.knowntypedata)
            if ktd:
                s.knowntypedata = ktd
        return s 

class __extend__(pairtype(SomeString, SomeString)):

    def union((str1, str2)):
        return SomeString(can_be_None=str1.can_be_None or str2.can_be_None)

    def add((str1, str2)):
        return SomeString()

class __extend__(pairtype(SomeChar, SomeChar)):

    def union((chr1, chr2)):
        return SomeChar()

class __extend__(pairtype(SomeUnicodeCodePoint, SomeUnicodeCodePoint)):

    def union((uchr1, uchr2)):
        return SomeUnicodeCodePoint()

class __extend__(pairtype(SomeString, SomeObject)):

    def mod((str, args)):
        return SomeString()


class __extend__(pairtype(SomeFloat, SomeFloat)):
    
    def union((flt1, flt2)):
        return SomeFloat()

    add = sub = mul = div = truediv = floordiv = mod = union

    def pow((flt1, flt2), obj3):
        return SomeFloat()


class __extend__(pairtype(SomeList, SomeList)):

    def union((lst1, lst2)):
        return SomeList(lst1.listdef.union(lst2.listdef))

    add = union

    def inplace_add((lst1, lst2)):   # force the union of lst1 and lst2
        lst1.listdef.resize()
        lst1.listdef.union(lst2.listdef)
        return lst1


class __extend__(pairtype(SomeList, SomeObject)):

    def inplace_add((lst1, obj2)):
        lst1.listdef.resize()
        s_iter = obj2.iter()
        pair(lst1, SomeInteger()).setitem(s_iter.next())
        return lst1

    def inplace_mul((lst1, obj2)):
        lst1.listdef.resize()
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
        return SomeDict(dic1.dictdef.union(dic2.dictdef))


class __extend__(pairtype(SomeDict, SomeObject)):

    def getitem((dic1, obj2)):
        return dic1.dictdef.read_value()

    def setitem((dic1, obj2), s_value):
        dic1.dictdef.generalize_key(obj2)
        dic1.dictdef.generalize_value(s_value)

    def delitem((dic1, obj1)):
        pass


class __extend__(pairtype(SomeSlice, SomeSlice)):

    def union((slic1, slic2)):
        return SomeSlice(unionof(slic1.start, slic2.start),
                         unionof(slic1.stop, slic2.stop),
                         unionof(slic1.step, slic2.step))


class __extend__(pairtype(SomeTuple, SomeInteger)):
    
    def getitem((tup1, int2)):
        if int2.is_constant():
            try:
                return tup1.items[int2.const]
            except IndexError:
                return SomeImpossibleValue()
        else:
            getbookkeeper().count("tuple_random_getitem", tup1)
            return unionof(*tup1.items)


class __extend__(pairtype(SomeList, SomeInteger)):
    
    def mul((lst1, int2)):
        return getbookkeeper().newlist(lst1.listdef.read_item())

    def getitem((lst1, int2)):
        getbookkeeper().count("list_getitem", int2)
        return lst1.listdef.read_item()

    def setitem((lst1, int2), s_value):
        getbookkeeper().count("list_setitem", int2)        
        lst1.listdef.mutate()
        lst1.listdef.generalize(s_value)

    def delitem((lst1, int2)):
        getbookkeeper().count("list_delitem", int2)        
        lst1.listdef.resize()

class __extend__(pairtype(SomeList, SomeSlice)):

    def getitem((lst, slic)):
        return getbookkeeper().newlist(lst.listdef.read_item())

    def setitem((lst, slic), s_iterable):
        lst.listdef.resize()
        s_iter = s_iterable.iter()
        pair(lst, SomeInteger()).setitem(s_iter.next())

    def delitem((lst1, slic)):
        lst1.listdef.resize()

class __extend__(pairtype(SomeString, SomeSlice)):

    def getitem((str1, slic)):
        return SomeString()

class __extend__(pairtype(SomeString, SomeInteger)):

    def getitem((str1, int2)):
        getbookkeeper().count("str_getitem", int2)        
        return SomeChar()

    def mul((str1, int2)): # xxx do we want to support this
        return SomeString()

class __extend__(pairtype(SomeInteger, SomeString)):
    
    def mul((int1, str2)): # xxx do we want to support this
        return SomeString()

class __extend__(pairtype(SomeInteger, SomeList)):
    
    def mul((int1, lst2)):
        return getbookkeeper().newlist(lst2.listdef.read_item())


class __extend__(pairtype(SomeInstance, SomeInstance)):

    def union((ins1, ins2)):
        basedef = ins1.classdef.commonbase(ins2.classdef)
        if basedef is None:
            # print warning?
            return SomeObject()
        return SomeInstance(basedef, can_be_None=ins1.can_be_None or ins2.can_be_None)

class __extend__(pairtype(SomeIterator, SomeIterator)):

    def union((iter1, iter2)):
        return SomeIterator(unionof(iter1.s_container, iter2.s_container))


class __extend__(pairtype(SomeBuiltin, SomeBuiltin)):

    def union((bltn1, bltn2)):
        if bltn1.analyser != bltn2.analyser or bltn1.methodname != bltn2.methodname:
            raise UnionError("merging incompatible builtins == BAD!")
        else:
            s_self = unionof(bltn1.s_self, bltn2.s_self)
            return SomeBuiltin(bltn1.analyser, s_self, methodname=bltn1.methodname)

class __extend__(pairtype(SomePBC, SomePBC)):
    def union((pbc1, pbc2)):       
        if len(pbc2.prebuiltinstances) > len(pbc1.prebuiltinstances):
            pbc1, pbc2 = pbc2, pbc1
        d = pbc1.prebuiltinstances.copy()
        for x, classdef in pbc2.prebuiltinstances.items():
            if x in d:
                if bool(isclassdef(classdef)) ^ bool(isclassdef(d[x])):
                    raise UnionError(
                        "union failed for %r with classdefs %r and %r" % 
                        (x, classdef, d[x]))
                if isclassdef(classdef):
                    classdef2 = classdef
                    if classdef != d[x]:
                        classdef = classdef.commonbase(d[x])
                        for cand in classdef.getmro():
                            if x in cand.cls.__dict__.values():
                                classdef = cand
                                break
                        else:
                            raise UnionError(
                                "confused pbc union trying unwarranted"
                                "moving up of method %s from pair %s %s" %
                                (x, d[x], classdef2))
            d[x] = classdef
        result =  SomePBC(d)
        return result

class __extend__(pairtype(SomeImpossibleValue, SomeObject)):
    def union((imp1, obj2)):
        return obj2

class __extend__(pairtype(SomeObject, SomeImpossibleValue)):
    def union((obj1, imp2)):
        return obj1

class __extend__(pairtype(SomeInstance, SomePBC)):
    def union((ins, pbc)):
        if pbc.isNone():
            return SomeInstance(classdef=ins.classdef, can_be_None = True)
        classdef = ins.classdef.superdef_containing(pbc.knowntype)
        if classdef is None:
            # print warning?
            return SomeObject()
        if not getattr(TLS, 'no_side_effects_in_union', 0):
            raise UnionError("mixing pbc and instance not supported anymore:  %s %s" % (pbc, ins))
        return SomeInstance(classdef)

class __extend__(pairtype(SomePBC, SomeInstance)):
    def union((pbc, ins)):
        return pair(ins, pbc).union()

# let mix lists and None for now
class __extend__(pairtype(SomeList, SomePBC)):
    def union((lst, pbc)):
        if pbc.isNone():
            return lst
        return SomeObject()

class __extend__(pairtype(SomePBC, SomeList    )):
    def union((pbc, lst)):
        return pair(lst, pbc).union()

# mixing strings and None

class __extend__(pairtype(SomeString, SomePBC)):
    def union((s, pbc)):
        if pbc.isNone():
            return SomeString(can_be_None=True)
        return SomeObject()

class __extend__(pairtype(SomePBC, SomeString    )):
    def union((pbc, s)):
        return pair(s, pbc).union()

# getitem on SomePBCs, in particular None fails

class __extend__(pairtype(SomePBC, SomeObject)):
    def getitem((pbc, o)):
        return SomeImpossibleValue()

# annotation of low-level types
from pypy.annotation.model import SomePtr, ll_to_annotation, annotation_to_lltype

class __extend__(pairtype(SomePtr, SomePtr)):
    def union((p1, p2)):
        assert p1.ll_ptrtype == p2.ll_ptrtype,("mixing of incompatible pointer types: %r, %r" %
                                               (p1.ll_ptrtype, p2.ll_ptrtype))
        return SomePtr(p1.ll_ptrtype)

class __extend__(pairtype(SomePtr, SomeInteger)):

    def getitem((p, int1)):
        v = p.ll_ptrtype._example()[0]
        return ll_to_annotation(v)

    def setitem((p, int1), s_value):
        v_lltype = annotation_to_lltype(s_value)
        p.ll_ptrtype._example()[0] = v_lltype._defl()

class __extend__(pairtype(SomePtr, SomeObject)):
    def union((p, obj)):
        assert False, ("mixing pointer type %r with something else %r" % (p.ll_ptrtype, obj))

    def gettitem((p, obj)):
        assert False,"ptr %r getitem index not an int: %r" % (p.ll_ptrtype, obj)

    def settitem((p, obj)):
        assert False,"ptr %r setitem index not an int: %r" % (p.ll_ptrtype, obj)

class __extend__(pairtype(SomeObject, SomePtr)):
    def union((obj, p2)):
        return pair(p2, obj).union()


