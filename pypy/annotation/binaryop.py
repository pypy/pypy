"""
Binary operations between SomeValues.
"""

import py
import operator
from pypy.tool.pairtype import pair, pairtype
from pypy.annotation.model import SomeObject, SomeInteger, SomeBool, s_Bool
from pypy.annotation.model import SomeString, SomeChar, SomeList, SomeDict
from pypy.annotation.model import SomeUnicodeCodePoint
from pypy.annotation.model import SomeTuple, SomeImpossibleValue, s_ImpossibleValue
from pypy.annotation.model import SomeInstance, SomeBuiltin, SomeIterator
from pypy.annotation.model import SomePBC, SomeSlice, SomeFloat, s_None
from pypy.annotation.model import SomeExternalObject, SomeWeakRef
from pypy.annotation.model import SomeAddress, SomeTypedAddressAccess
from pypy.annotation.model import SomeSingleFloat
from pypy.annotation.model import unionof, UnionError, set, missing_operation
from pypy.annotation.model import isdegenerated, TLS
from pypy.annotation.model import read_can_only_throw
from pypy.annotation.model import add_knowntypedata, merge_knowntypedata
from pypy.annotation.model import SomeGenericCallable
from pypy.annotation.model import SomeExternalInstance, SomeUnicodeString
from pypy.annotation.bookkeeper import getbookkeeper
from pypy.objspace.flow.model import Variable, Constant
from pypy.rlib import rarithmetic

# convenience only!
def immutablevalue(x):
    return getbookkeeper().immutablevalue(x)

def unioncheck(*somevalues):
    s_value = unionof(*somevalues)
    if isdegenerated(s_value):
        if not getattr(TLS, 'no_side_effects_in_union', 0):
            bookkeeper = getbookkeeper()
            if bookkeeper is not None:
                bookkeeper.ondegenerated('union', s_value)
    return s_value

# XXX unify this with ObjSpace.MethodTable
BINARY_OPERATIONS = set(['add', 'sub', 'mul', 'div', 'mod',
                         'truediv', 'floordiv', 'divmod', 'pow',
                         'and_', 'or_', 'xor',
                         'lshift', 'rshift',
                         'getitem', 'setitem', 'delitem',
                         'getitem_idx', 'getitem_key', 'getitem_idx_key',
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
            if obj1.is_immutable_constant() and obj2.is_immutable_constant() and obj1.const == obj2.const:
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
                result = obj1
            elif obj2 == result:
                result = obj2
            unioncheck(result)
            return result

    # inplace_xxx ---> xxx by default
    def inplace_add((obj1, obj2)):      return pair(obj1, obj2).add()
    def inplace_sub((obj1, obj2)):      return pair(obj1, obj2).sub()
    def inplace_mul((obj1, obj2)):      return pair(obj1, obj2).mul()
    def inplace_truediv((obj1, obj2)):  return pair(obj1, obj2).truediv()
    def inplace_floordiv((obj1, obj2)): return pair(obj1, obj2).floordiv()
    def inplace_div((obj1, obj2)):      return pair(obj1, obj2).div()
    def inplace_mod((obj1, obj2)):      return pair(obj1, obj2).mod()
    def inplace_pow((obj1, obj2)):      return pair(obj1, obj2).pow(s_None)
    def inplace_lshift((obj1, obj2)):   return pair(obj1, obj2).lshift()
    def inplace_rshift((obj1, obj2)):   return pair(obj1, obj2).rshift()
    def inplace_and((obj1, obj2)):      return pair(obj1, obj2).and_()
    def inplace_or((obj1, obj2)):       return pair(obj1, obj2).or_()
    def inplace_xor((obj1, obj2)):      return pair(obj1, obj2).xor()

    for name, func in locals().items():
        if name.startswith('inplace_'):
            func.can_only_throw = []

    inplace_div.can_only_throw = [ZeroDivisionError]
    inplace_truediv.can_only_throw = [ZeroDivisionError]
    inplace_floordiv.can_only_throw = [ZeroDivisionError]
    inplace_mod.can_only_throw = [ZeroDivisionError]

    def lt((obj1, obj2)):
        if obj1.is_immutable_constant() and obj2.is_immutable_constant():
            return immutablevalue(obj1.const < obj2.const)
        else:
            getbookkeeper().count("non_int_comp", obj1, obj2)
            return s_Bool

    def le((obj1, obj2)):
        if obj1.is_immutable_constant() and obj2.is_immutable_constant():
            return immutablevalue(obj1.const <= obj2.const)
        else:
            getbookkeeper().count("non_int_comp", obj1, obj2)
            return s_Bool

    def eq((obj1, obj2)):
        if obj1.is_immutable_constant() and obj2.is_immutable_constant():
            return immutablevalue(obj1.const == obj2.const)
        else:
            getbookkeeper().count("non_int_eq", obj1, obj2)
            return s_Bool

    def ne((obj1, obj2)):
        if obj1.is_immutable_constant() and obj2.is_immutable_constant():
            return immutablevalue(obj1.const != obj2.const)
        else:
            getbookkeeper().count("non_int_eq", obj1, obj2)
            return s_Bool

    def gt((obj1, obj2)):
        if obj1.is_immutable_constant() and obj2.is_immutable_constant():
            return immutablevalue(obj1.const > obj2.const)
        else:
            getbookkeeper().count("non_int_comp", obj1, obj2)
            return s_Bool

    def ge((obj1, obj2)):
        if obj1.is_immutable_constant() and obj2.is_immutable_constant():
            return immutablevalue(obj1.const >= obj2.const)
        else:
            getbookkeeper().count("non_int_comp", obj1, obj2)
            return s_Bool

    def cmp((obj1, obj2)):
        getbookkeeper().count("cmp", obj1, obj2)
        if obj1.is_immutable_constant() and obj2.is_immutable_constant():
            return immutablevalue(cmp(obj1.const, obj2.const))
        else:
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
        getbookkeeper().count("divmod", obj1, obj2)
        return SomeTuple([pair(obj1, obj2).div(), pair(obj1, obj2).mod()])

    def coerce((obj1, obj2)):
        getbookkeeper().count("coerce", obj1, obj2)
        return pair(obj1, obj2).union()   # reasonable enough

    # approximation of an annotation intersection, the result should be the annotation obj or 
    # the intersection of obj and improvement
    def improve((obj, improvement)):
        if not improvement.contains(obj) and obj.contains(improvement):
            return improvement
        else:
            return obj

    # checked getitems

    def _getitem_can_only_throw(s_c1, s_o2):
        impl = pair(s_c1, s_o2).getitem
        return read_can_only_throw(impl, s_c1, s_o2)

    def getitem_idx_key((s_c1, s_o2)):
        impl = pair(s_c1, s_o2).getitem
        return impl()
    getitem_idx_key.can_only_throw = _getitem_can_only_throw

    getitem_idx = getitem_idx_key
    getitem_key = getitem_idx_key
        

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
        knowntype = rarithmetic.compute_restype(int1.knowntype, int2.knowntype)
        return SomeInteger(nonneg=int1.nonneg and int2.nonneg,
                           knowntype=knowntype)

    or_ = xor = add = mul = _clone(union, [])
    add_ovf = mul_ovf = _clone(union, [OverflowError])
    div = floordiv = mod = _clone(union, [ZeroDivisionError])
    div_ovf= floordiv_ovf = mod_ovf = _clone(union, [ZeroDivisionError, OverflowError])

    def truediv((int1, int2)):
        return SomeFloat()
    truediv.can_only_throw = [ZeroDivisionError]
    truediv_ovf = _clone(truediv, [ZeroDivisionError, OverflowError])

    inplace_div = div
    inplace_truediv = truediv

    def sub((int1, int2)):
        knowntype = rarithmetic.compute_restype(int1.knowntype, int2.knowntype)
        return SomeInteger(knowntype=knowntype)
    sub.can_only_throw = []
    sub_ovf = _clone(sub, [OverflowError])

    def and_((int1, int2)):
        knowntype = rarithmetic.compute_restype(int1.knowntype, int2.knowntype)
        return SomeInteger(nonneg=int1.nonneg or int2.nonneg,
                           knowntype=knowntype)
    and_.can_only_throw = []

    def lshift((int1, int2)):
        return SomeInteger(knowntype=int1.knowntype)

    lshift_ovf = _clone(lshift, [ValueError, OverflowError])

    def rshift((int1, int2)):
        return SomeInteger(nonneg=int1.nonneg, knowntype=int1.knowntype)
    rshift.can_only_throw = [ValueError]

    def pow((int1, int2), obj3):
        knowntype = rarithmetic.compute_restype(int1.knowntype, int2.knowntype)
        return SomeInteger(nonneg = int1.nonneg,
                           knowntype=knowntype)
    pow.can_only_throw = [ZeroDivisionError]
    pow_ovf = _clone(pow, [ZeroDivisionError, OverflowError])

    def inplace_pow((int1, int2)):
        knowntype = rarithmetic.compute_restype(int1.knowntype, int2.knowntype)
        return SomeInteger(nonneg = int1.nonneg,
                           knowntype=knowntype)
    inplace_pow.can_only_throw = [ZeroDivisionError]

    def _compare_helper((int1, int2), opname, operation):
        r = SomeBool()
        if int1.is_immutable_constant() and int2.is_immutable_constant():
            r.const = operation(int1.const, int2.const)
        #
        # The rest of the code propagates nonneg information between
        # the two arguments.
        #
        # Doing the right thing when int1 or int2 change from signed
        # to unsigned (r_uint) is almost impossible.  See test_intcmp_bug.
        # Instead, we only deduce constrains on the operands in the
        # case where they are both signed.  In other words, if y is
        # nonneg then "assert x>=y" will let the annotator know that
        # x is nonneg too, but it will not work if y is unsigned.
        #
        if not (rarithmetic.signedtype(int1.knowntype) and
                rarithmetic.signedtype(int2.knowntype)):
            return r
        knowntypedata = {}
        # XXX HACK HACK HACK
        fn, block, i = getbookkeeper().position_key
        op = block.operations[i]
        assert op.opname == opname
        assert len(op.args) == 2
        def tointtype(int0):
            if int0.knowntype is bool:
                return int
            return int0.knowntype
        if int1.nonneg and isinstance(op.args[1], Variable):
            case = opname in ('lt', 'le', 'eq')
                
            add_knowntypedata(knowntypedata, case, [op.args[1]],
                              SomeInteger(nonneg=True, knowntype=tointtype(int2)))
        if int2.nonneg and isinstance(op.args[0], Variable):
            case = opname in ('gt', 'ge', 'eq')
            add_knowntypedata(knowntypedata, case, [op.args[0]],
                              SomeInteger(nonneg=True, knowntype=tointtype(int1)))
        if knowntypedata:
            r.knowntypedata = knowntypedata
        # a special case for 'x < 0' or 'x >= 0',
        # where 0 is a flow graph Constant
        # (in this case we are sure that it cannot become a r_uint later)
        if (isinstance(op.args[1], Constant) and 
            type(op.args[1].value) is int and    # filter out Symbolics
            op.args[1].value == 0):
            if int1.nonneg:
                if opname == 'lt':
                    r.const = False
                if opname == 'ge':
                    r.const = True
        return r

    def lt(intint): return intint._compare_helper('lt', operator.lt)
    def le(intint): return intint._compare_helper('le', operator.le)
    def eq(intint): return intint._compare_helper('eq', operator.eq)
    def ne(intint): return intint._compare_helper('ne', operator.ne)
    def gt(intint): return intint._compare_helper('gt', operator.gt)
    def ge(intint): return intint._compare_helper('ge', operator.ge)

class __extend__(pairtype(SomeBool, SomeInteger)):
    def lshift((int1, int2)):
        return SomeInteger()

    lshift.can_only_throw = [ValueError]
    lshift_ovf = _clone(lshift, [ValueError, OverflowError])

    def rshift((int1, int2)):
        return SomeInteger(nonneg=True)
    rshift.can_only_throw = [ValueError]

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

    def and_((boo1, boo2)):
        s = SomeBool()
        if boo1.is_constant():
            if not boo1.const:
                s.const = False
            else:
                return boo2
        if boo2.is_constant():
            if not boo2.const:
                s.const = False
        return s

    def or_((boo1, boo2)):
        s = SomeBool()
        if boo1.is_constant():
            if boo1.const:
                s.const = True
            else:
                return boo2
        if boo2.is_constant():
            if boo2.const:
                s.const = True
        return s
        
    def xor((boo1, boo2)):
        s = SomeBool()
        if boo1.is_constant() and boo2.is_constant():
            s.const = boo1.const ^ boo2.const
        return s
        
class __extend__(pairtype(SomeString, SomeString)):

    def union((str1, str2)):
        return SomeString(can_be_None=str1.can_be_None or str2.can_be_None)

    def add((str1, str2)):
        # propagate const-ness to help getattr(obj, 'prefix' + const_name)
        result = SomeString()
        if str1.is_immutable_constant() and str2.is_immutable_constant():
            result.const = str1.const + str2.const
        return result

class __extend__(pairtype(SomeChar, SomeChar)):

    def union((chr1, chr2)):
        return SomeChar()


class __extend__(pairtype(SomeChar, SomeUnicodeCodePoint),
                 pairtype(SomeUnicodeCodePoint, SomeChar)):
    def union((uchr1, uchr2)):
        return SomeUnicodeCodePoint()

class __extend__(pairtype(SomeUnicodeCodePoint, SomeUnicodeCodePoint)):
    def union((uchr1, uchr2)):
        return SomeUnicodeCodePoint()

    def add((chr1, chr2)):
        return SomeUnicodeString()

class __extend__(pairtype(SomeString, SomeUnicodeString),
                 pairtype(SomeString, SomeUnicodeString)):
    def mod((str, unistring)):
        raise NotImplementedError(
            "string formatting mixing strings and unicode not supported")


class __extend__(pairtype(SomeString, SomeTuple)):
    def mod((str, s_tuple)):
        for s_item in s_tuple.items:
            if isinstance(s_item, (SomeUnicodeCodePoint, SomeUnicodeString)):
                raise NotImplementedError(
                    "string formatting mixing strings and unicode not supported")
        getbookkeeper().count('strformat', str, s_tuple)
        return SomeString()


class __extend__(pairtype(SomeString, SomeObject)):

    def mod((str, args)):
        getbookkeeper().count('strformat', str, args)
        return SomeString()

class __extend__(pairtype(SomeFloat, SomeFloat)):
    
    def union((flt1, flt2)):
        return SomeFloat()

    add = sub = mul = union

    def div((flt1, flt2)):
        return SomeFloat()
    div.can_only_throw = []
    truediv = div

    def pow((flt1, flt2), obj3):
        raise NotImplementedError("float power not supported, use math.pow")

    # repeat these in order to copy the 'can_only_throw' attribute
    inplace_div = div
    inplace_truediv = truediv


class __extend__(pairtype(SomeSingleFloat, SomeSingleFloat)):
    
    def union((flt1, flt2)):
        return SomeSingleFloat()


class __extend__(pairtype(SomeList, SomeList)):

    def union((lst1, lst2)):
        return SomeList(lst1.listdef.union(lst2.listdef))

    def add((lst1, lst2)):
        return lst1.listdef.offspring(lst2.listdef)

    def eq((lst1, lst2)):
        lst1.listdef.agree(lst2.listdef)
        return s_Bool
    ne = eq


class __extend__(pairtype(SomeList, SomeObject)):

    def inplace_add((lst1, obj2)):
        lst1.method_extend(obj2)
        return lst1
    inplace_add.can_only_throw = []

    def inplace_mul((lst1, obj2)):
        lst1.listdef.resize()
        return lst1
    inplace_mul.can_only_throw = []

class __extend__(pairtype(SomeTuple, SomeTuple)):

    def union((tup1, tup2)):
        if len(tup1.items) != len(tup2.items):
            return SomeObject()
        else:
            unions = [unioncheck(x,y) for x,y in zip(tup1.items, tup2.items)]
            return SomeTuple(items = unions)

    def add((tup1, tup2)):
        return SomeTuple(items = tup1.items + tup2.items)


class __extend__(pairtype(SomeDict, SomeDict)):

    def union((dic1, dic2)):
        return SomeDict(dic1.dictdef.union(dic2.dictdef))


class __extend__(pairtype(SomeDict, SomeObject)):

    def _can_only_throw(dic1, *ignore):
        if dic1.dictdef.dictkey.custom_eq_hash:
            return None
        return [KeyError]

    def getitem((dic1, obj2)):
        getbookkeeper().count("dict_getitem", dic1)
        dic1.dictdef.generalize_key(obj2)
        return dic1.dictdef.read_value()
    getitem.can_only_throw = _can_only_throw

    def setitem((dic1, obj2), s_value):
        getbookkeeper().count("dict_setitem", dic1)
        dic1.dictdef.generalize_key(obj2)
        dic1.dictdef.generalize_value(s_value)
    setitem.can_only_throw = _can_only_throw

    def delitem((dic1, obj2)):
        getbookkeeper().count("dict_delitem", dic1)
        dic1.dictdef.generalize_key(obj2)
    delitem.can_only_throw = _can_only_throw


class __extend__(pairtype(SomeSlice, SomeSlice)):

    def union((slic1, slic2)):
        return SomeSlice(unioncheck(slic1.start, slic2.start),
                         unioncheck(slic1.stop, slic2.stop),
                         unioncheck(slic1.step, slic2.step))


class __extend__(pairtype(SomeTuple, SomeInteger)):
    
    def getitem((tup1, int2)):
        if int2.is_immutable_constant():
            try:
                return tup1.items[int2.const]
            except IndexError:
                return s_ImpossibleValue
        else:
            getbookkeeper().count("tuple_random_getitem", tup1)
            return unionof(*tup1.items)
    getitem.can_only_throw = [IndexError]

class __extend__(pairtype(SomeTuple, SomeSlice)):

    def getitem((tup, slic)):
        start, stop, step = slic.constant_indices()
        return SomeTuple(tup.items[start:stop:step])
    getitem.can_only_throw = []


class __extend__(pairtype(SomeList, SomeInteger)):
    
    def mul((lst1, int2)):
        return lst1.listdef.offspring()

    def getitem((lst1, int2)):
        getbookkeeper().count("list_getitem", int2)
        return lst1.listdef.read_item()
    getitem.can_only_throw = []

    getitem_key = getitem

    def getitem_idx((lst1, int2)):
        getbookkeeper().count("list_getitem", int2)
        return lst1.listdef.read_item()
    getitem_idx.can_only_throw = [IndexError]

    getitem_idx_key = getitem_idx

    def setitem((lst1, int2), s_value):
        getbookkeeper().count("list_setitem", int2)        
        lst1.listdef.mutate()
        lst1.listdef.generalize(s_value)
    setitem.can_only_throw = [IndexError]

    def delitem((lst1, int2)):
        getbookkeeper().count("list_delitem", int2)        
        lst1.listdef.resize()
    delitem.can_only_throw = [IndexError]

def check_negative_slice(s_slice):
    if isinstance(s_slice.start, SomeInteger) and not s_slice.start.nonneg:
        raise TypeError("%s not proven to have non-negative start" % s_slice)
    if isinstance(s_slice.stop, SomeInteger) and not s_slice.stop.nonneg and\
           getattr(s_slice.stop, 'const', 0) != -1:
        raise TypeError("%s not proven to have non-negative stop" % s_slice)

class __extend__(pairtype(SomeList, SomeSlice)):

    def getitem((lst, slic)):
        check_negative_slice(slic)
        return lst.listdef.offspring()
    getitem.can_only_throw = []

    def setitem((lst, slic), s_iterable):
        check_negative_slice(slic)
        # we need the same unifying effect as the extend() method for
        # the case lst1[x:y] = lst2.
        lst.method_extend(s_iterable)
    setitem.can_only_throw = []

    def delitem((lst1, slic)):
        check_negative_slice(slic)
        lst1.listdef.resize()
    delitem.can_only_throw = []

class __extend__(pairtype(SomeString, SomeSlice),
                 pairtype(SomeUnicodeString, SomeSlice)):

    def getitem((str1, slic)):
        check_negative_slice(slic)
        return str1.basestringclass()
    getitem.can_only_throw = []

class __extend__(pairtype(SomeString, SomeInteger)):

    def getitem((str1, int2)):
        getbookkeeper().count("str_getitem", int2)        
        return SomeChar()
    getitem.can_only_throw = []

    getitem_key = getitem

    def getitem_idx((str1, int2)):
        getbookkeeper().count("str_getitem", int2)        
        return SomeChar()        
    getitem_idx.can_only_throw = [IndexError]

    getitem_idx_key = getitem_idx

    def mul((str1, int2)): # xxx do we want to support this
        getbookkeeper().count("str_mul", str1, int2)
        return SomeString()

class __extend__(pairtype(SomeUnicodeString, SomeInteger)):
    def getitem((str1, int2)):
        getbookkeeper().count("str_getitem", int2)        
        return SomeUnicodeCodePoint()
    getitem.can_only_throw = []

    getitem_key = getitem

    def getitem_idx((str1, int2)):
        getbookkeeper().count("str_getitem", int2)        
        return SomeUnicodeCodePoint()
    getitem_idx.can_only_throw = [IndexError]

    getitem_idx_key = getitem_idx

    def mul((str1, int2)): # xxx do we want to support this
        getbookkeeper().count("str_mul", str1, int2)
        return SomeUnicodeString()

class __extend__(pairtype(SomeInteger, SomeString),
                 pairtype(SomeInteger, SomeUnicodeString)):
    
    def mul((int1, str2)): # xxx do we want to support this
        getbookkeeper().count("str_mul", str2, int1)
        return str2.basestringclass()

class __extend__(pairtype(SomeUnicodeCodePoint, SomeUnicodeString),
                 pairtype(SomeUnicodeString, SomeUnicodeCodePoint),
                 pairtype(SomeUnicodeString, SomeUnicodeString)):
    def union((str1, str2)):
        return SomeUnicodeString(can_be_None=str1.can_be_none() or
                                 str2.can_be_none())

    def add((str1, str2)):
        # propagate const-ness to help getattr(obj, 'prefix' + const_name)
        result = SomeUnicodeString()
        if str1.is_immutable_constant() and str2.is_immutable_constant():
            result.const = str1.const + str2.const
        return result

class __extend__(pairtype(SomeInteger, SomeList)):
    
    def mul((int1, lst2)):
        return lst2.listdef.offspring()


class __extend__(pairtype(SomeInstance, SomeInstance)):

    def union((ins1, ins2)):
        if ins1.classdef is None or ins2.classdef is None:
            # special case only
            basedef = None
        else:
            basedef = ins1.classdef.commonbase(ins2.classdef)
            if basedef is None:
                # print warning?
                return SomeObject()
        flags = ins1.flags
        if flags:
            flags = flags.copy()
            for key, value in flags.items():
                if key not in ins2.flags or ins2.flags[key] != value:
                    del flags[key]
        return SomeInstance(basedef,
                            can_be_None=ins1.can_be_None or ins2.can_be_None,
                            flags=flags)

    def improve((ins1, ins2)):
        if ins1.classdef is None:
            resdef = ins2.classdef
        elif ins2.classdef is None:
            resdef = ins1.classdef
        else:
            basedef = ins1.classdef.commonbase(ins2.classdef)
            if basedef is ins1.classdef:
                resdef = ins2.classdef
            elif basedef is ins2.classdef:
                resdef = ins1.classdef
            else:
                if ins1.can_be_None and ins2.can_be_None:
                    return s_None
                else:
                    return s_ImpossibleValue
        res = SomeInstance(resdef, can_be_None=ins1.can_be_None and ins2.can_be_None)
        if ins1.contains(res) and ins2.contains(res):
            return res    # fine
        else:
            # this case can occur in the presence of 'const' attributes,
            # which we should try to preserve.  Fall-back...
            thistype = pairtype(SomeInstance, SomeInstance)
            return super(thistype, pair(ins1, ins2)).improve()


class __extend__(pairtype(SomeIterator, SomeIterator)):

    def union((iter1, iter2)):
        s_cont = unioncheck(iter1.s_container, iter2.s_container)
        if iter1.variant != iter2.variant:
            raise UnionError("merging incompatible iterators variants")
        return SomeIterator(s_cont, *iter1.variant)


class __extend__(pairtype(SomeBuiltin, SomeBuiltin)):

    def union((bltn1, bltn2)):
        if (bltn1.analyser != bltn2.analyser or
            bltn1.methodname != bltn2.methodname or
            bltn1.s_self is None or bltn2.s_self is None):
            raise UnionError("cannot merge two different builtin functions "
                             "or methods:\n  %r\n  %r" % (bltn1, bltn2))
        s_self = unioncheck(bltn1.s_self, bltn2.s_self)
        return SomeBuiltin(bltn1.analyser, s_self, methodname=bltn1.methodname)

class __extend__(pairtype(SomePBC, SomePBC)):

    def union((pbc1, pbc2)):       
        d = pbc1.descriptions.copy()
        d.update(pbc2.descriptions)
        return SomePBC(d, can_be_None = pbc1.can_be_None or pbc2.can_be_None)

    def is_((pbc1, pbc2)):
        thistype = pairtype(SomePBC, SomePBC)
        s = super(thistype, pair(pbc1, pbc2)).is_()
        if not s.is_constant():
            if not pbc1.can_be_None or not pbc2.can_be_None:
                for desc in pbc1.descriptions:
                    if desc in pbc2.descriptions:
                        break
                else:
                    s.const = False    # no common desc in the two sets
        return s

class __extend__(pairtype(SomeGenericCallable, SomePBC)):
    def union((gencall, pbc)):
        for desc in pbc.descriptions:
            unique_key = desc
            bk = desc.bookkeeper
            s_result = bk.emulate_pbc_call(unique_key, pbc, gencall.args_s)
            s_result = unioncheck(s_result, gencall.s_result)
            assert gencall.s_result.contains(s_result)
        return gencall

class __extend__(pairtype(SomePBC, SomeGenericCallable)):
    def union((pbc, gencall)):
        return pair(gencall, pbc).union()

class __extend__(pairtype(SomeImpossibleValue, SomeObject)):
    def union((imp1, obj2)):
        return obj2

class __extend__(pairtype(SomeObject, SomeImpossibleValue)):
    def union((obj1, imp2)):
        return obj1

# mixing Nones with other objects

def _make_none_union(classname, constructor_args='', glob=None):
    if glob is None:
        glob = globals()
    loc = locals()
    source = py.code.Source("""
        class __extend__(pairtype(%(classname)s, SomePBC)):
            def union((obj, pbc)):
                if pbc.isNone():
                    return %(classname)s(%(constructor_args)s)
                else:
                    return SomeObject()

        class __extend__(pairtype(SomePBC, %(classname)s)):
            def union((pbc, obj)):
                if pbc.isNone():
                    return %(classname)s(%(constructor_args)s)
                else:
                    return SomeObject()
    """ % loc)
    exec source.compile() in glob

_make_none_union('SomeInstance',   'classdef=obj.classdef, can_be_None=True')
_make_none_union('SomeString',      'can_be_None=True')
_make_none_union('SomeUnicodeString', 'can_be_None=True')
_make_none_union('SomeList',         'obj.listdef')
_make_none_union('SomeDict',          'obj.dictdef')
_make_none_union('SomeExternalObject', 'obj.knowntype')
_make_none_union('SomeWeakRef',         'obj.classdef')

# getitem on SomePBCs, in particular None fails

class __extend__(pairtype(SomePBC, SomeObject)):
    def getitem((pbc, o)):
        return s_ImpossibleValue

class __extend__(pairtype(SomeExternalObject, SomeExternalObject)):
    def union((ext1, ext2)):
        if ext1.knowntype == ext2.knowntype:
            return SomeExternalObject(ext1.knowntype)
        return SomeObject()

class __extend__(pairtype(SomeExternalInstance, SomeExternalInstance)):
    def union((ext1, ext2)):
        def commonsuperclass(cls1, cls2):
            cls = cls2
            while not issubclass(cls1, cls):
                cls = cls.__bases__[0]
            return cls
        
        from pypy.rpython.ootypesystem.bltregistry import BasicExternal
        cls = commonsuperclass(ext1.knowntype, ext2.knowntype)
        if cls is BasicExternal:
            return SomeObject()
        return SomeExternalInstance(cls)

# ____________________________________________________________
# annotation of low-level types
from pypy.annotation.model import SomePtr, SomeOOInstance, SomeOOClass
from pypy.annotation.model import ll_to_annotation, annotation_to_lltype
from pypy.rpython.ootypesystem import ootype

_make_none_union('SomeOOInstance', 'ootype=obj.ootype, can_be_None=True')

class __extend__(pairtype(SomePtr, SomePtr)):
    def union((p1, p2)):
        assert p1.ll_ptrtype == p2.ll_ptrtype,("mixing of incompatible pointer types: %r, %r" %
                                               (p1.ll_ptrtype, p2.ll_ptrtype))
        return SomePtr(p1.ll_ptrtype)

class __extend__(pairtype(SomePtr, SomeInteger)):

    def getitem((p, int1)):
        example = p.ll_ptrtype._example()
        try:
            v = example[0]
        except IndexError:
            return None       # impossible value, e.g. FixedSizeArray(0)
        return ll_to_annotation(v)
    getitem.can_only_throw = []

    def setitem((p, int1), s_value):   # just doing checking
        example = p.ll_ptrtype._example()
        if example[0] is not None:  # ignore Void s_value
            v_lltype = annotation_to_lltype(s_value)
            example[0] = v_lltype._defl()
    setitem.can_only_throw = []

class __extend__(pairtype(SomePtr, SomeObject)):
    def union((p, obj)):
        assert False, ("mixing pointer type %r with something else %r" % (p.ll_ptrtype, obj))

    def getitem((p, obj)):
        assert False,"ptr %r getitem index not an int: %r" % (p.ll_ptrtype, obj)

    def setitem((p, obj)):
        assert False,"ptr %r setitem index not an int: %r" % (p.ll_ptrtype, obj)

class __extend__(pairtype(SomeObject, SomePtr)):
    def union((obj, p2)):
        return pair(p2, obj).union()


class __extend__(pairtype(SomeOOInstance, SomeOOInstance)):
    def union((r1, r2)):
        common = ootype.commonBaseclass(r1.ootype, r2.ootype)
        assert common is not None, 'Mixing of incompatible instances %r, %r' %(r1.ootype, r2.ootype)
        return SomeOOInstance(common, can_be_None=r1.can_be_None or r2.can_be_None)

class __extend__(pairtype(SomeOOClass, SomeOOClass)):
    def union((r1, r2)):
        if r1.ootype is None:
            common = r2.ootype
        elif r2.ootype is None:
            common = r1.ootype
        else:
            common = ootype.commonBaseclass(r1.ootype, r2.ootype)
            assert common is not None, ('Mixing of incompatible classes %r, %r'
                                        % (r1.ootype, r2.ootype))
        return SomeOOClass(common)

class __extend__(pairtype(SomeOOInstance, SomeObject)):
    def union((r, obj)):
        assert False, ("mixing reference type %r with something else %r" % (r.ootype, obj))

class __extend__(pairtype(SomeObject, SomeOOInstance)):
    def union((obj, r2)):
        return pair(r2, obj).union()


#_________________________________________
# weakrefs

class __extend__(pairtype(SomeWeakRef, SomeWeakRef)):
    def union((s_wrf1, s_wrf2)):
        if s_wrf1.classdef is None:
            basedef = s_wrf2.classdef   # s_wrf1 is known to be dead
        elif s_wrf2.classdef is None:
            basedef = s_wrf1.classdef   # s_wrf2 is known to be dead
        else:
            basedef = s_wrf1.classdef.commonbase(s_wrf2.classdef)
            if basedef is None:    # no common base class! complain...
                return SomeObject()
        return SomeWeakRef(basedef)

#_________________________________________
# memory addresses

class __extend__(pairtype(SomeAddress, SomeAddress)):
    def union((s_addr1, s_addr2)):
        return SomeAddress(is_null=s_addr1.is_null and s_addr2.is_null)

    def sub((s_addr1, s_addr2)):
        if s_addr1.is_null and s_addr2.is_null:
            return getbookkeeper().immutablevalue(0)
        return SomeInteger()

    def is_((s_addr1, s_addr2)):
        assert False, "comparisons with is not supported by addresses"

class __extend__(pairtype(SomeTypedAddressAccess, SomeTypedAddressAccess)):
    def union((s_taa1, s_taa2)):
        assert s_taa1.type == s_taa2.type
        return s_taa1

class __extend__(pairtype(SomeTypedAddressAccess, SomeInteger)):
    def getitem((s_taa, s_int)):
        from pypy.annotation.model import lltype_to_annotation
        return lltype_to_annotation(s_taa.type)
    getitem.can_only_throw = []

    def setitem((s_taa, s_int), s_value):
        from pypy.annotation.model import annotation_to_lltype
        assert annotation_to_lltype(s_value) is s_taa.type
    setitem.can_only_throw = []


class __extend__(pairtype(SomeAddress, SomeInteger)):
    def add((s_addr, s_int)):
        return SomeAddress(is_null=False)

    def sub((s_addr, s_int)):
        return SomeAddress(is_null=False)

class __extend__(pairtype(SomeAddress, SomeImpossibleValue)):
    # need to override this specifically to hide the 'raise UnionError'
    # of pairtype(SomeAddress, SomeObject).
    def union((s_addr, s_imp)):
        return s_addr

class __extend__(pairtype(SomeImpossibleValue, SomeAddress)):
    # need to override this specifically to hide the 'raise UnionError'
    # of pairtype(SomeObject, SomeAddress).
    def union((s_imp, s_addr)):
        return s_addr

class __extend__(pairtype(SomeAddress, SomeObject)):
    def union((s_addr, s_obj)):
        raise UnionError, "union of address and anything else makes no sense"

class __extend__(pairtype(SomeObject, SomeAddress)):
    def union((s_obj, s_addr)):
        raise UnionError, "union of address and anything else makes no sense"
