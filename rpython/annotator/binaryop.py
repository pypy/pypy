"""
Binary operations between SomeValues.
"""

import py
import operator
from rpython.tool.pairtype import pair, pairtype
from rpython.annotator.model import SomeObject, SomeInteger, SomeBool, s_Bool
from rpython.annotator.model import SomeString, SomeChar, SomeList, SomeDict,\
     SomeOrderedDict
from rpython.annotator.model import SomeUnicodeCodePoint, SomeUnicodeString
from rpython.annotator.model import SomeTuple, SomeImpossibleValue, s_ImpossibleValue
from rpython.annotator.model import SomeInstance, SomeBuiltin, SomeIterator
from rpython.annotator.model import SomePBC, SomeFloat, s_None, SomeByteArray
from rpython.annotator.model import SomeWeakRef
from rpython.annotator.model import SomeAddress, SomeTypedAddressAccess
from rpython.annotator.model import SomeSingleFloat, SomeLongFloat, SomeType
from rpython.annotator.model import unionof, UnionError, missing_operation
from rpython.annotator.model import read_can_only_throw
from rpython.annotator.model import add_knowntypedata, merge_knowntypedata
from rpython.annotator.bookkeeper import getbookkeeper
from rpython.flowspace.model import Variable, Constant
from rpython.rlib import rarithmetic
from rpython.annotator.model import AnnotatorError

# convenience only!
def immutablevalue(x):
    return getbookkeeper().immutablevalue(x)

# XXX unify this with ObjSpace.MethodTable
BINARY_OPERATIONS = set(['add', 'sub', 'mul', 'div', 'mod',
                         'truediv', 'floordiv', 'divmod',
                         'and_', 'or_', 'xor',
                         'lshift', 'rshift',
                         'getitem', 'setitem', 'delitem',
                         'getitem_idx', 'getitem_key', 'getitem_idx_key',
                         'inplace_add', 'inplace_sub', 'inplace_mul',
                         'inplace_truediv', 'inplace_floordiv', 'inplace_div',
                         'inplace_mod',
                         'inplace_lshift', 'inplace_rshift',
                         'inplace_and', 'inplace_or', 'inplace_xor',
                         'lt', 'le', 'eq', 'ne', 'gt', 'ge', 'is_', 'cmp',
                         'coerce',
                         ]
                        +[opname+'_ovf' for opname in
                          """add sub mul floordiv div mod lshift
                           """.split()
                          ])

for opname in BINARY_OPERATIONS:
    missing_operation(pairtype(SomeObject, SomeObject), opname)

class __extend__(pairtype(SomeObject, SomeObject)):

    def union((obj1, obj2)):
        raise UnionError(obj1, obj2)

    # inplace_xxx ---> xxx by default
    def inplace_add((obj1, obj2)):      return pair(obj1, obj2).add()
    def inplace_sub((obj1, obj2)):      return pair(obj1, obj2).sub()
    def inplace_mul((obj1, obj2)):      return pair(obj1, obj2).mul()
    def inplace_truediv((obj1, obj2)):  return pair(obj1, obj2).truediv()
    def inplace_floordiv((obj1, obj2)): return pair(obj1, obj2).floordiv()
    def inplace_div((obj1, obj2)):      return pair(obj1, obj2).div()
    def inplace_mod((obj1, obj2)):      return pair(obj1, obj2).mod()
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
            op = bk._find_current_op("is_", 2)
            knowntypedata = {}
            annotator = bk.annotator

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
            r.set_knowntypedata(knowntypedata)

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


class __extend__(pairtype(SomeType, SomeType)):

    def union((obj1, obj2)):
        result = SomeType()
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
        return result


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
        if int1.unsigned == int2.unsigned:
            knowntype = rarithmetic.compute_restype(int1.knowntype, int2.knowntype)
        else:
            t1 = int1.knowntype
            if t1 is bool:
                t1 = int
            t2 = int2.knowntype
            if t2 is bool:
                t2 = int

            if t2 is int:
                if int2.nonneg == False:
                    raise UnionError(int1, int2, "RPython cannot prove that these " + \
                            "integers are of the same signedness")
                knowntype = t1
            elif t1 is int:
                if int1.nonneg == False:
                    raise UnionError(int1, int2, "RPython cannot prove that these " + \
                            "integers are of the same signedness")
                knowntype = t2
            else:
                raise UnionError(int1, int2)
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
        if isinstance(int1, SomeBool):
            return SomeInteger()
        else:
            return SomeInteger(knowntype=int1.knowntype)
    lshift.can_only_throw = []
    lshift_ovf = _clone(lshift, [OverflowError])

    def rshift((int1, int2)):
        if isinstance(int1, SomeBool):
            return SomeInteger(nonneg=True)
        else:
            return SomeInteger(nonneg=int1.nonneg, knowntype=int1.knowntype)
    rshift.can_only_throw = []

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
        op = getbookkeeper()._find_current_op(opname=opname, arity=2)
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
        r.set_knowntypedata(knowntypedata)
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


class __extend__(pairtype(SomeBool, SomeBool)):

    def union((boo1, boo2)):
        s = SomeBool()
        if getattr(boo1, 'const', -1) == getattr(boo2, 'const', -2):
            s.const = boo1.const
        if hasattr(boo1, 'knowntypedata') and \
           hasattr(boo2, 'knowntypedata'):
            ktd = merge_knowntypedata(boo1.knowntypedata, boo2.knowntypedata)
            s.set_knowntypedata(ktd)
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
        can_be_None = str1.can_be_None or str2.can_be_None
        no_nul = str1.no_nul and str2.no_nul
        return SomeString(can_be_None=can_be_None, no_nul=no_nul)

    def add((str1, str2)):
        # propagate const-ness to help getattr(obj, 'prefix' + const_name)
        result = SomeString(no_nul=str1.no_nul and str2.no_nul)
        if str1.is_immutable_constant() and str2.is_immutable_constant():
            result.const = str1.const + str2.const
        return result

class __extend__(pairtype(SomeByteArray, SomeByteArray)):
    def union((b1, b2)):
        can_be_None = b1.can_be_None or b2.can_be_None
        return SomeByteArray(can_be_None=can_be_None)

    def add((b1, b2)):
        result = SomeByteArray()
        if b1.is_immutable_constant() and b2.is_immutable_constant():
            result.const = b1.const + b2.const
        return result

class __extend__(pairtype(SomeByteArray, SomeInteger)):
    def getitem((s_b, s_i)):
        return SomeInteger()

    def setitem((s_b, s_i), s_i2):
        assert isinstance(s_i2, SomeInteger)

class __extend__(pairtype(SomeString, SomeByteArray),
                 pairtype(SomeByteArray, SomeString),
                 pairtype(SomeChar, SomeByteArray),
                 pairtype(SomeByteArray, SomeChar)):
    def add((b1, b2)):
        result = SomeByteArray()
        if b1.is_immutable_constant() and b2.is_immutable_constant():
            result.const = b1.const + b2.const
        return result

class __extend__(pairtype(SomeChar, SomeChar)):

    def union((chr1, chr2)):
        no_nul = chr1.no_nul and chr2.no_nul
        return SomeChar(no_nul=no_nul)


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
                 pairtype(SomeUnicodeString, SomeString)):
    def mod((str, unistring)):
        raise AnnotatorError(
            "string formatting mixing strings and unicode not supported")


class __extend__(pairtype(SomeString, SomeTuple),
                 pairtype(SomeUnicodeString, SomeTuple)):
    def mod((s_string, s_tuple)):
        is_string = isinstance(s_string, SomeString)
        is_unicode = isinstance(s_string, SomeUnicodeString)
        assert is_string or is_unicode
        for s_item in s_tuple.items:
            if (is_unicode and isinstance(s_item, (SomeChar, SomeString)) or
                is_string and isinstance(s_item, (SomeUnicodeCodePoint,
                                                  SomeUnicodeString))):
                raise AnnotatorError(
                    "string formatting mixing strings and unicode not supported")
        getbookkeeper().count('strformat', s_string, s_tuple)
        no_nul = s_string.no_nul
        for s_item in s_tuple.items:
            if isinstance(s_item, SomeFloat):
                pass   # or s_item is a subclass, like SomeInteger
            elif (isinstance(s_item, SomeString) or
                  isinstance(s_item, SomeUnicodeString)) and s_item.no_nul:
                pass
            else:
                no_nul = False
                break
        return s_string.__class__(no_nul=no_nul)


class __extend__(pairtype(SomeString, SomeObject),
                 pairtype(SomeUnicodeString, SomeObject)):

    def mod((s_string, args)):
        getbookkeeper().count('strformat', s_string, args)
        return s_string.__class__()

class __extend__(pairtype(SomeFloat, SomeFloat)):

    def union((flt1, flt2)):
        return SomeFloat()

    add = sub = mul = union

    def div((flt1, flt2)):
        return SomeFloat()
    div.can_only_throw = []
    truediv = div

    # repeat these in order to copy the 'can_only_throw' attribute
    inplace_div = div
    inplace_truediv = truediv


class __extend__(pairtype(SomeSingleFloat, SomeSingleFloat)):

    def union((flt1, flt2)):
        return SomeSingleFloat()


class __extend__(pairtype(SomeLongFloat, SomeLongFloat)):

    def union((flt1, flt2)):
        return SomeLongFloat()


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
            raise UnionError(tup1, tup2, "RPython cannot unify tuples of "
                    "different length: %d versus %d" % \
                    (len(tup1.items), len(tup2.items)))
        else:
            unions = [unionof(x,y) for x,y in zip(tup1.items, tup2.items)]
            return SomeTuple(items = unions)

    def add((tup1, tup2)):
        return SomeTuple(items = tup1.items + tup2.items)

    def eq(tup1tup2):
        tup1tup2.union()
        return s_Bool
    ne = eq

    def lt((tup1, tup2)):
        raise Exception("unsupported: (...) < (...)")
    def le((tup1, tup2)):
        raise Exception("unsupported: (...) <= (...)")
    def gt((tup1, tup2)):
        raise Exception("unsupported: (...) > (...)")
    def ge((tup1, tup2)):
        raise Exception("unsupported: (...) >= (...)")


class __extend__(pairtype(SomeDict, SomeDict)):

    def union((dic1, dic2)):
        assert dic1.__class__ == dic2.__class__
        return dic1.__class__(dic1.dictdef.union(dic2.dictdef))


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

class __extend__(pairtype(SomeString, SomeInteger)):

    def getitem((str1, int2)):
        getbookkeeper().count("str_getitem", int2)
        return SomeChar(no_nul=str1.no_nul)
    getitem.can_only_throw = []

    getitem_key = getitem

    def getitem_idx((str1, int2)):
        getbookkeeper().count("str_getitem", int2)
        return SomeChar(no_nul=str1.no_nul)
    getitem_idx.can_only_throw = [IndexError]

    getitem_idx_key = getitem_idx

    def mul((str1, int2)): # xxx do we want to support this
        getbookkeeper().count("str_mul", str1, int2)
        return SomeString(no_nul=str1.no_nul)

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
                raise UnionError(ins1, ins2, "RPython cannot unify instances "
                        "with no common base class")
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
        s_cont = unionof(iter1.s_container, iter2.s_container)
        if iter1.variant != iter2.variant:
            raise UnionError(iter1, iter2,
                    "RPython cannot unify incompatible iterator variants")
        return SomeIterator(s_cont, *iter1.variant)


class __extend__(pairtype(SomeBuiltin, SomeBuiltin)):

    def union((bltn1, bltn2)):
        if (bltn1.analyser != bltn2.analyser or
            bltn1.methodname != bltn2.methodname or
            bltn1.s_self is None or bltn2.s_self is None):
            raise UnionError(bltn1, bltn2)
        s_self = unionof(bltn1.s_self, bltn2.s_self)
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
                    raise UnionError(pbc, obj)

        class __extend__(pairtype(SomePBC, %(classname)s)):
            def union((pbc, obj)):
                if pbc.isNone():
                    return %(classname)s(%(constructor_args)s)
                else:
                    raise UnionError(pbc, obj)
    """ % loc)
    exec source.compile() in glob

_make_none_union('SomeInstance',   'classdef=obj.classdef, can_be_None=True')
_make_none_union('SomeString',      'no_nul=obj.no_nul, can_be_None=True')
_make_none_union('SomeUnicodeString', 'can_be_None=True')
_make_none_union('SomeList',         'obj.listdef')
_make_none_union('SomeOrderedDict',          'obj.dictdef')
_make_none_union('SomeDict',          'obj.dictdef')
_make_none_union('SomeWeakRef',         'obj.classdef')

# getitem on SomePBCs, in particular None fails

class __extend__(pairtype(SomePBC, SomeObject)):
    def getitem((pbc, o)):
        if not pbc.isNone():
            raise AnnotatorError("getitem on %r" % pbc)
        return s_ImpossibleValue

    def setitem((pbc, o), s_value):
        if not pbc.isNone():
            raise AnnotatorError("setitem on %r" % pbc)

class __extend__(pairtype(SomePBC, SomeString)):
    def add((pbc, o)):
        if not pbc.isNone():
            raise AnnotatorError('add on %r' % pbc)
        return s_ImpossibleValue

class __extend__(pairtype(SomeString, SomePBC)):
    def add((o, pbc)):
        if not pbc.isNone():
            raise AnnotatorError('add on %r' % pbc)
        return s_ImpossibleValue

# ____________________________________________________________
# annotation of low-level types
from rpython.annotator.model import SomePtr
from rpython.annotator.model import ll_to_annotation, annotation_to_lltype

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

    def setitem((p, obj), s_value):
        assert False,"ptr %r setitem index not an int: %r" % (p.ll_ptrtype, obj)

class __extend__(pairtype(SomeObject, SomePtr)):
    def union((obj, p2)):
        return pair(p2, obj).union()


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
        return SomeAddress()

    def sub((s_addr1, s_addr2)):
        if s_addr1.is_null_address() and s_addr2.is_null_address():
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
        from rpython.annotator.model import lltype_to_annotation
        return lltype_to_annotation(s_taa.type)
    getitem.can_only_throw = []

    def setitem((s_taa, s_int), s_value):
        from rpython.annotator.model import annotation_to_lltype
        assert annotation_to_lltype(s_value) is s_taa.type
    setitem.can_only_throw = []


class __extend__(pairtype(SomeAddress, SomeInteger)):
    def add((s_addr, s_int)):
        return SomeAddress()

    def sub((s_addr, s_int)):
        return SomeAddress()

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
        raise UnionError(s_addr, s_obj)

class __extend__(pairtype(SomeObject, SomeAddress)):
    def union((s_obj, s_addr)):
        raise UnionError(s_obj, s_addr)
