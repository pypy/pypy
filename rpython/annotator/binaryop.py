"""
Binary operations between SomeValues.
"""
from collections import defaultdict

from rpython.tool.pairtype import pair, pairtype
from rpython.annotator.model import (
    SomeObject, SomeInteger, SomeBool, s_Bool, SomeString, SomeChar, SomeList,
    SomeDict, SomeUnicodeCodePoint, SomeUnicodeString, SomeException,
    SomeTuple, SomeImpossibleValue, s_ImpossibleValue, SomeInstance,
    SomeBuiltinMethod, SomeIterator, SomePBC, SomeNone, SomeFloat, s_None,
    SomeByteArray, SomeWeakRef, SomeSingleFloat,
    SomeLongFloat, SomeType, SomeTypeOf, SomeConstantType, unionof, UnionError,
    union, read_can_only_throw, add_knowntypedata,
    merge_knowntypedata,)
from rpython.annotator.bookkeeper import immutablevalue, getbookkeeper
from rpython.flowspace.model import Variable, Constant, const
from rpython.flowspace.operation import op
from rpython.rlib import rarithmetic
from rpython.annotator.model import AnnotatorError, TLS

BINARY_OPERATIONS = set([oper.opname for oper in op.__dict__.values()
                        if oper.dispatch == 2])


@op.is_.register(SomeObject, SomeObject)
def is__default(annotator, obj1, obj2):
    r = SomeBool()
    s_obj1 = annotator.annotation(obj1)
    s_obj2 = annotator.annotation(obj2)
    if s_obj2.is_constant():
        if s_obj1.is_constant():
            r.const = s_obj1.const is s_obj2.const
        if s_obj2.const is None and not s_obj1.can_be_none():
            r.const = False
    elif s_obj1.is_constant():
        if s_obj1.const is None and not s_obj2.can_be_none():
            r.const = False
    knowntypedata = defaultdict(dict)
    bk = annotator.bookkeeper

    def bind(src_obj, tgt_obj):
        s_src = annotator.annotation(src_obj)
        s_tgt = annotator.annotation(tgt_obj)
        if hasattr(s_tgt, 'is_type_of') and s_src.is_constant():
            add_knowntypedata(
                knowntypedata, True,
                s_tgt.is_type_of,
                bk.valueoftype(s_src.const))
        add_knowntypedata(knowntypedata, True, [tgt_obj], s_src)
        s_nonnone = s_tgt
        if (s_src.is_constant() and s_src.const is None and
                s_tgt.can_be_none()):
            s_nonnone = s_tgt.nonnoneify()
        add_knowntypedata(knowntypedata, False, [tgt_obj], s_nonnone)

    bind(obj2, obj1)
    bind(obj1, obj2)
    r.set_knowntypedata(knowntypedata)
    return r

def _make_cmp_annotator_default(cmp_op):
    @cmp_op.register(SomeObject, SomeObject)
    def default_annotate(annotator, obj1, obj2):
        s_1, s_2 = annotator.annotation(obj1), annotator.annotation(obj2)
        if s_1.is_immutable_constant() and s_2.is_immutable_constant():
            return immutablevalue(cmp_op.pyfunc(s_1.const, s_2.const))
        else:
            return s_Bool

for cmp_op in [op.lt, op.le, op.eq, op.ne, op.gt, op.ge]:
    _make_cmp_annotator_default(cmp_op)

@op.getitem.register(SomeObject, SomeObject)
def getitem_default(ann, v_obj, v_index):
    return s_ImpossibleValue

def _getitem_can_only_throw(s_c1, s_o2):
    impl = op.getitem.get_specialization(s_c1, s_o2)
    return read_can_only_throw(impl, s_c1, s_o2)

@op.getitem_idx.register(SomeObject, SomeObject)
def getitem_idx(ann, v_obj, v_index):
    s_obj = ann.annotation(v_obj)
    s_index = ann.annotation(v_index)
    impl = op.getitem.get_specialization(s_obj, s_index)
    return impl(ann, v_obj, v_index)
getitem_idx.can_only_throw = _getitem_can_only_throw

class __extend__(pairtype(SomeObject, SomeObject)):

    def union(args):
        raise UnionError(*args)

    # inplace_xxx ---> xxx by default
    def inplace_add(args):      return pair(*args).add()
    def inplace_sub(args):      return pair(*args).sub()
    def inplace_mul(args):      return pair(*args).mul()
    def inplace_truediv(args):  return pair(*args).truediv()
    def inplace_floordiv(args): return pair(*args).floordiv()
    def inplace_div(args):      return pair(*args).div()
    def inplace_mod(args):      return pair(*args).mod()
    def inplace_lshift(args):   return pair(*args).lshift()
    def inplace_rshift(args):   return pair(*args).rshift()
    def inplace_and(args):      return pair(*args).and_()
    def inplace_or(args):       return pair(*args).or_()
    def inplace_xor(args):      return pair(*args).xor()

    for name, func in locals().copy().items():
        if name.startswith('inplace_'):
            locals()[name].can_only_throw = []

    inplace_div.can_only_throw = [ZeroDivisionError]
    inplace_truediv.can_only_throw = [ZeroDivisionError]
    inplace_floordiv.can_only_throw = [ZeroDivisionError]
    inplace_mod.can_only_throw = [ZeroDivisionError]

    def cmp(args):
        obj1, obj2 = args
        if obj1.is_immutable_constant() and obj2.is_immutable_constant():
            return immutablevalue(cmp(obj1.const, obj2.const))
        else:
            return SomeInteger()

    def divmod(args):
        obj1, obj2 = args
        return SomeTuple([pair(obj1, obj2).div(), pair(obj1, obj2).mod()])

    def coerce(args):
        obj1, obj2 = args
        return pair(obj1, obj2).union()   # reasonable enough

    def add(args):
        obj1, obj2 = args
        return s_ImpossibleValue
    sub = mul = truediv = floordiv = div = mod = add
    lshift = rshift = and_ = or_ = xor = delitem = add

    def setitem(args, _):
        obj1, obj2 = args
        return s_ImpossibleValue

    # approximation of an annotation intersection, the result should be the annotation obj or
    # the intersection of obj and improvement
    def improve(args):
        obj, improvement = args
        if not improvement.contains(obj) and obj.contains(improvement):
            return improvement
        else:
            return obj



class __extend__(pairtype(SomeType, SomeType),
                 pairtype(SomeType, SomeConstantType),
                 pairtype(SomeConstantType, SomeType),):

    def union(args):
        obj1, obj2 = args
        result = SomeType()
        if obj1.is_immutable_constant() and obj2.is_immutable_constant() and obj1.const == obj2.const:
            result.const = obj1.const
        return result

class __extend__(pairtype(SomeTypeOf, SomeTypeOf)):
    def union(args):
        s_obj1, s_obj2 = args
        vars = list(set(s_obj1.is_type_of) | set(s_obj2.is_type_of))
        result = SomeTypeOf(vars)
        if (s_obj1.is_immutable_constant() and s_obj2.is_immutable_constant()
                and s_obj1.const == s_obj2.const):
            result.const = obj1.const
        return result

# cloning a function with identical code, for the can_only_throw attribute
def _clone(f, can_only_throw = None):
    newfunc = type(f)(f.__code__, f.__globals__, f.__name__,
                      f.__defaults__, f.__closure__)
    if can_only_throw is not None:
        newfunc.can_only_throw = can_only_throw
    return newfunc

class __extend__(pairtype(SomeInteger, SomeInteger)):
    # unsignedness is considered a rare and contagious disease

    def union(args):
        int1, int2 = args
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

    def truediv(args):
        int1, int2 = args
        return SomeFloat()
    truediv.can_only_throw = [ZeroDivisionError]
    truediv_ovf = _clone(truediv, [ZeroDivisionError, OverflowError])

    inplace_div = div
    inplace_truediv = truediv

    def sub(args):
        int1, int2 = args
        knowntype = rarithmetic.compute_restype(int1.knowntype, int2.knowntype)
        return SomeInteger(knowntype=knowntype)
    sub.can_only_throw = []
    sub_ovf = _clone(sub, [OverflowError])

    def and_(args):
        int1, int2 = args
        knowntype = rarithmetic.compute_restype(int1.knowntype, int2.knowntype)
        return SomeInteger(nonneg=int1.nonneg or int2.nonneg,
                           knowntype=knowntype)
    and_.can_only_throw = []

    def lshift(args):
        int1, int2 = args
        if isinstance(int1, SomeBool):
            return SomeInteger()
        else:
            return SomeInteger(knowntype=int1.knowntype)
    lshift.can_only_throw = []
    lshift_ovf = _clone(lshift, [OverflowError])

    def rshift(args):
        int1, int2 = args
        if isinstance(int1, SomeBool):
            return SomeInteger(nonneg=True)
        else:
            return SomeInteger(nonneg=int1.nonneg, knowntype=int1.knowntype)
    rshift.can_only_throw = []


def _make_cmp_annotator_int(cmp_op):
    @cmp_op.register(SomeInteger, SomeInteger)
    def _compare_helper(annotator, int1, int2):
        r = SomeBool()
        s_int1, s_int2 = annotator.annotation(int1), annotator.annotation(int2)
        if s_int1.is_immutable_constant() and s_int2.is_immutable_constant():
            r.const = cmp_op.pyfunc(s_int1.const, s_int2.const)
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
        if not (rarithmetic.signedtype(s_int1.knowntype) and
                rarithmetic.signedtype(s_int2.knowntype)):
            return r
        knowntypedata = defaultdict(dict)
        def tointtype(s_int0):
            if s_int0.knowntype is bool:
                return int
            return s_int0.knowntype
        if s_int1.nonneg and isinstance(int2, Variable):
            case = cmp_op.opname in ('lt', 'le', 'eq')
            add_knowntypedata(knowntypedata, case, [int2],
                              SomeInteger(nonneg=True, knowntype=tointtype(s_int2)))
        if s_int2.nonneg and isinstance(int1, Variable):
            case = cmp_op.opname in ('gt', 'ge', 'eq')
            add_knowntypedata(knowntypedata, case, [int1],
                              SomeInteger(nonneg=True, knowntype=tointtype(s_int1)))
        r.set_knowntypedata(knowntypedata)
        # a special case for 'x < 0' or 'x >= 0',
        # where 0 is a flow graph Constant
        # (in this case we are sure that it cannot become a r_uint later)
        if (isinstance(int2, Constant) and
                type(int2.value) is int and  # filter out Symbolics
                int2.value == 0):
            if s_int1.nonneg:
                if cmp_op.opname == 'lt':
                    r.const = False
                if cmp_op.opname == 'ge':
                    r.const = True
        return r

for cmp_op in [op.lt, op.le, op.eq, op.ne, op.gt, op.ge]:
    _make_cmp_annotator_int(cmp_op)

class __extend__(pairtype(SomeBool, SomeBool)):

    def union(args):
        boo1, boo2 = args
        s = SomeBool()
        if getattr(boo1, 'const', -1) == getattr(boo2, 'const', -2):
            s.const = boo1.const
        if hasattr(boo1, 'knowntypedata') and \
           hasattr(boo2, 'knowntypedata'):
            ktd = merge_knowntypedata(boo1.knowntypedata, boo2.knowntypedata)
            s.set_knowntypedata(ktd)
        return s

    def and_(args):
        boo1, boo2 = args
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

    def or_(args):
        boo1, boo2 = args
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

    def xor(args):
        boo1, boo2 = args
        s = SomeBool()
        if boo1.is_constant() and boo2.is_constant():
            s.const = boo1.const ^ boo2.const
        return s

class __extend__(pairtype(SomeString, SomeString)):

    def union(args):
        str1, str2 = args
        can_be_None = str1.can_be_None or str2.can_be_None
        no_nul = str1.no_nul and str2.no_nul
        return SomeString(can_be_None=can_be_None, no_nul=no_nul)

    def add(args):
        str1, str2 = args
        # propagate const-ness to help getattr(obj, 'prefix' + const_name)
        result = SomeString(no_nul=str1.no_nul and str2.no_nul)
        if str1.is_immutable_constant() and str2.is_immutable_constant():
            result.const = str1.const + str2.const
        return result

class __extend__(pairtype(SomeByteArray, SomeByteArray)):
    def union(args):
        b1, b2 = args
        can_be_None = b1.can_be_None or b2.can_be_None
        return SomeByteArray(can_be_None=can_be_None)

    def add(args):
        b1, b2 = args
        return SomeByteArray()

class __extend__(pairtype(SomeByteArray, SomeInteger)):
    def getitem(args):
        s_b, s_i = args
        return SomeInteger()

    def setitem(args, s_i2):
        s_b, s_i = args
        assert isinstance(s_i2, SomeInteger)

class __extend__(pairtype(SomeString, SomeByteArray),
                 pairtype(SomeByteArray, SomeString),
                 pairtype(SomeChar, SomeByteArray),
                 pairtype(SomeByteArray, SomeChar)):
    def add(args):
        b1, b2 = args
        return SomeByteArray()

class __extend__(pairtype(SomeChar, SomeChar)):

    def union(args):
        chr1, chr2 = args
        no_nul = chr1.no_nul and chr2.no_nul
        return SomeChar(no_nul=no_nul)


class __extend__(pairtype(SomeUnicodeCodePoint, SomeUnicodeCodePoint)):
    def union(args):
        uchr1, uchr2 = args
        no_nul = uchr1.no_nul and uchr2.no_nul
        return SomeUnicodeCodePoint(no_nul=no_nul)

class __extend__(pairtype(SomeString, SomeUnicodeString),
                 pairtype(SomeUnicodeString, SomeString)):
    def mod(args):
        str, unistring = args
        raise AnnotatorError(
            "string formatting mixing strings and unicode not supported")


class __extend__(pairtype(SomeString, SomeTuple),
                 pairtype(SomeUnicodeString, SomeTuple)):
    def mod(args):
        s_string, s_tuple = args
        if not s_string.is_constant():
            raise AnnotatorError("string formatting requires a constant "
                                 "string/unicode on the left of '%'")
        is_string = isinstance(s_string, SomeString)
        is_unicode = isinstance(s_string, SomeUnicodeString)
        assert is_string or is_unicode
        for s_item in s_tuple.items:
            if (is_unicode and isinstance(s_item, (SomeChar, SomeString)) or
                is_string and isinstance(s_item, (SomeUnicodeCodePoint,
                                                  SomeUnicodeString))):
                raise AnnotatorError(
                    "string formatting mixing strings and unicode not supported")
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

    def mod(args):
        s_string, s_arg = args
        assert not isinstance(s_arg, SomeTuple)
        return pair(s_string, SomeTuple([s_arg])).mod()

class __extend__(pairtype(SomeFloat, SomeFloat)):

    def union(args):
        flt1, flt2 = args
        if not TLS.allow_int_to_float:
            # in this mode, if one of the two is actually the
            # subclass SomeInteger, complain
            if isinstance(flt1, SomeInteger) or isinstance(flt2, SomeInteger):
                raise UnionError(flt1, flt2)
        return SomeFloat()

    add = sub = mul = union

    def div(args):
        flt1, flt2 = args
        return SomeFloat()
    div.can_only_throw = []
    truediv = div

    # repeat these in order to copy the 'can_only_throw' attribute
    inplace_div = div
    inplace_truediv = truediv


class __extend__(pairtype(SomeSingleFloat, SomeSingleFloat)):

    def union(args):
        flt1, flt2 = args
        return SomeSingleFloat()


class __extend__(pairtype(SomeLongFloat, SomeLongFloat)):

    def union(args):
        flt1, flt2 = args
        return SomeLongFloat()


class __extend__(pairtype(SomeList, SomeList)):

    def union(args):
        lst1, lst2 = args
        return SomeList(lst1.listdef.union(lst2.listdef))

    def add(args):
        lst1, lst2 = args
        bk = getbookkeeper()
        return lst1.listdef.offspring(bk, lst2.listdef)

    def eq(args):
        lst1, lst2 = args
        lst1.listdef.agree(getbookkeeper(), lst2.listdef)
        return s_Bool
    ne = eq


class __extend__(pairtype(SomeList, SomeObject)):

    def inplace_add(args):
        lst1, obj2 = args
        lst1.method_extend(obj2)
        return lst1
    inplace_add.can_only_throw = []

    def inplace_mul(args):
        lst1, obj2 = args
        lst1.listdef.resize()
        return lst1
    inplace_mul.can_only_throw = []

class __extend__(pairtype(SomeTuple, SomeTuple)):

    def union(args):
        tup1, tup2 = args
        if len(tup1.items) != len(tup2.items):
            raise UnionError(tup1, tup2, "RPython cannot unify tuples of "
                    "different length: %d versus %d" % \
                    (len(tup1.items), len(tup2.items)))
        else:
            unions = [unionof(x,y) for x,y in zip(tup1.items, tup2.items)]
            return SomeTuple(items = unions)

    def add(args):
        tup1, tup2 = args
        return SomeTuple(items = tup1.items + tup2.items)

    def eq(tup1tup2):
        tup1tup2.union()
        return s_Bool
    ne = eq

    def lt(args):
        tup1, tup2 = args
        raise AnnotatorError("unsupported: (...) < (...)")
    def le(args):
        tup1, tup2 = args
        raise AnnotatorError("unsupported: (...) <= (...)")
    def gt(args):
        tup1, tup2 = args
        raise AnnotatorError("unsupported: (...) > (...)")
    def ge(args):
        tup1, tup2 = args
        raise AnnotatorError("unsupported: (...) >= (...)")


class __extend__(pairtype(SomeDict, SomeDict)):

    def union(args):
        dic1, dic2 = args
        assert dic1.__class__ == dic2.__class__
        return dic1.__class__(dic1.dictdef.union(dic2.dictdef))

    def ne(args):
        dic1, dic2 = args
        raise AnnotatorError("dict != dict not implemented")

def _dict_can_only_throw_keyerror(s_dct, *ignore):
    if s_dct.dictdef.dictkey.custom_eq_hash:
        return None    # r_dict: can throw anything
    return [KeyError]

def _dict_can_only_throw_nothing(s_dct, *ignore):
    if s_dct.dictdef.dictkey.custom_eq_hash:
        return None    # r_dict: can throw anything
    return []          # else: no possible exception

@op.getitem.register(SomeDict, SomeObject)
def getitem_SomeDict(annotator, v_dict, v_key):
    s_dict = annotator.annotation(v_dict)
    s_key = annotator.annotation(v_key)
    s_dict.dictdef.generalize_key(s_key)
    position = annotator.bookkeeper.position_key
    return s_dict.dictdef.read_value(position)
getitem_SomeDict.can_only_throw = _dict_can_only_throw_keyerror


class __extend__(pairtype(SomeDict, SomeObject)):

    def setitem(args, s_value):
        dic1, obj2 = args
        dic1.dictdef.generalize_key(obj2)
        dic1.dictdef.generalize_value(s_value)
    setitem.can_only_throw = _dict_can_only_throw_nothing

    def delitem(args):
        dic1, obj2 = args
        dic1.dictdef.generalize_key(obj2)
    delitem.can_only_throw = _dict_can_only_throw_keyerror


class __extend__(pairtype(SomeTuple, SomeInteger)):

    def getitem(args):
        tup1, int2 = args
        if int2.is_immutable_constant():
            try:
                return tup1.items[int2.const]
            except IndexError:
                return s_ImpossibleValue
        else:
            return unionof(*tup1.items)
    getitem.can_only_throw = [IndexError]


class __extend__(pairtype(SomeList, SomeInteger)):

    def mul(args):
        lst1, int2 = args
        bk = getbookkeeper()
        return lst1.listdef.offspring(bk)

    def getitem(args):
        lst1, int2 = args
        position = getbookkeeper().position_key
        return lst1.listdef.read_item(position)
    getitem.can_only_throw = []

    def getitem_idx(args):
        lst1, int2 = args
        position = getbookkeeper().position_key
        return lst1.listdef.read_item(position)
    getitem_idx.can_only_throw = [IndexError]

    def setitem(args, s_value):
        lst1, int2 = args
        lst1.listdef.mutate()
        lst1.listdef.generalize(s_value)
    setitem.can_only_throw = [IndexError]

    def delitem(args):
        lst1, int2 = args
        lst1.listdef.resize()
    delitem.can_only_throw = [IndexError]

class __extend__(pairtype(SomeString, SomeInteger)):

    def getitem(args):
        str1, int2 = args
        return SomeChar(no_nul=str1.no_nul)
    getitem.can_only_throw = []

    def getitem_idx(args):
        str1, int2 = args
        return SomeChar(no_nul=str1.no_nul)
    getitem_idx.can_only_throw = [IndexError]

    def mul(args):
        str1, int2 = args # xxx do we want to support this
        return SomeString(no_nul=str1.no_nul)

class __extend__(pairtype(SomeUnicodeString, SomeInteger)):
    def getitem(args):
        str1, int2 = args
        return SomeUnicodeCodePoint(no_nul=str1.no_nul)
    getitem.can_only_throw = []

    def getitem_idx(args):
        str1, int2 = args
        return SomeUnicodeCodePoint(no_nul=str1.no_nul)
    getitem_idx.can_only_throw = [IndexError]

    def mul(args):
        str1, int2 = args # xxx do we want to support this
        return SomeUnicodeString(no_nul=str1.no_nul)

class __extend__(pairtype(SomeInteger, SomeString),
                 pairtype(SomeInteger, SomeUnicodeString)):

    def mul(args):
        int1, str2 = args # xxx do we want to support this
        return str2.basestringclass(no_nul=str2.no_nul)

class __extend__(pairtype(SomeUnicodeCodePoint, SomeUnicodeString),
                 pairtype(SomeUnicodeString, SomeUnicodeCodePoint),
                 pairtype(SomeUnicodeString, SomeUnicodeString)):
    def union(args):
        str1, str2 = args
        can_be_None = str1.can_be_None or str2.can_be_None
        no_nul = str1.no_nul and str2.no_nul
        return SomeUnicodeString(can_be_None=can_be_None, no_nul=no_nul)

    def add(args):
        str1, str2 = args
        # propagate const-ness to help getattr(obj, 'prefix' + const_name)
        result = SomeUnicodeString(no_nul=str1.no_nul and str2.no_nul)
        if str1.is_immutable_constant() and str2.is_immutable_constant():
            result.const = str1.const + str2.const
        return result

for cmp_op in [op.lt, op.le, op.eq, op.ne, op.gt, op.ge]:
    @cmp_op.register(SomeUnicodeString, SomeString)
    @cmp_op.register(SomeUnicodeString, SomeChar)
    @cmp_op.register(SomeString, SomeUnicodeString)
    @cmp_op.register(SomeChar, SomeUnicodeString)
    @cmp_op.register(SomeUnicodeCodePoint, SomeString)
    @cmp_op.register(SomeUnicodeCodePoint, SomeChar)
    @cmp_op.register(SomeString, SomeUnicodeCodePoint)
    @cmp_op.register(SomeChar, SomeUnicodeCodePoint)
    def cmp_str_unicode(annotator, v1, v2):
        raise AnnotatorError(
            "Comparing byte strings with unicode strings is not RPython")


class __extend__(pairtype(SomeInteger, SomeList)):

    def mul(args):
        int1, lst2 = args
        bk = getbookkeeper()
        return lst2.listdef.offspring(bk)


class __extend__(pairtype(SomeInstance, SomeInstance)):

    def union(args):
        ins1, ins2 = args
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

    def improve(args):
        ins1, ins2 = args
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

class __extend__(
        pairtype(SomeException, SomeInstance),
        pairtype(SomeException, SomeNone)):
    def union(args):
        s_exc, s_inst = args
        return union(s_exc.as_SomeInstance(), s_inst)

class __extend__(
        pairtype(SomeInstance, SomeException),
        pairtype(SomeNone, SomeException)):
    def union(args):
        s_inst, s_exc = args
        return union(s_exc.as_SomeInstance(), s_inst)

class __extend__(pairtype(SomeException, SomeException)):
    def union(args):
        s_exc1, s_exc2 = args
        return SomeException(s_exc1.classdefs | s_exc2.classdefs)


@op.getitem.register_transform(SomeInstance, SomeObject)
def getitem_SomeInstance(annotator, v_ins, v_idx):
    get_getitem = op.getattr(v_ins, const('__getitem__'))
    return [get_getitem, op.simple_call(get_getitem.result, v_idx)]

@op.setitem.register_transform(SomeInstance, SomeObject)
def setitem_SomeInstance(annotator, v_ins, v_idx, v_value):
    get_setitem = op.getattr(v_ins, const('__setitem__'))
    return [get_setitem,
            op.simple_call(get_setitem.result, v_idx, v_value)]

@op.contains.register_transform(SomeInstance)
def contains_SomeInstance(annotator, v_ins, v_idx):
    get_contains = op.getattr(v_ins, const('__contains__'))
    return [get_contains, op.simple_call(get_contains.result, v_idx)]

class __extend__(pairtype(SomeIterator, SomeIterator)):

    def union(args):
        iter1, iter2 = args
        s_cont = unionof(iter1.s_container, iter2.s_container)
        if iter1.variant != iter2.variant:
            raise UnionError(iter1, iter2,
                    "RPython cannot unify incompatible iterator variants")
        return SomeIterator(s_cont, *iter1.variant)


class __extend__(pairtype(SomeBuiltinMethod, SomeBuiltinMethod)):
    def union(args):
        bltn1, bltn2 = args
        if (bltn1.analyser != bltn2.analyser or
                bltn1.methodname != bltn2.methodname):
            raise UnionError(bltn1, bltn2)
        s_self = unionof(bltn1.s_self, bltn2.s_self)
        return SomeBuiltinMethod(bltn1.analyser, s_self,
                methodname=bltn1.methodname)

@op.is_.register(SomePBC, SomePBC)
def is__PBC_PBC(annotator, pbc1, pbc2):
    s = is__default(annotator, pbc1, pbc2)
    if not s.is_constant():
        s_pbc1 = annotator.annotation(pbc1)
        s_pbc2 = annotator.annotation(pbc2)
        if not s_pbc1.can_be_None or not s_pbc2.can_be_None:
            for desc in s_pbc1.descriptions:
                if desc in s_pbc2.descriptions:
                    break
            else:
                s.const = False    # no common desc in the two sets
    return s

class __extend__(pairtype(SomePBC, SomePBC)):
    def union(args):
        pbc1, pbc2 = args
        d = pbc1.descriptions.copy()
        d.update(pbc2.descriptions)
        return SomePBC(d, can_be_None = pbc1.can_be_None or pbc2.can_be_None)

class __extend__(pairtype(SomeImpossibleValue, SomeObject)):
    def union(args):
        imp1, obj2 = args
        return obj2

class __extend__(pairtype(SomeObject, SomeImpossibleValue)):
    def union(args):
        obj1, imp2 = args
        return obj1

# mixing Nones with other objects

class __extend__(pairtype(SomeObject, SomeNone)):
    def union(args):
        obj, none = args
        return obj.noneify()

class __extend__(pairtype(SomeNone, SomeObject)):
    def union(args):
        none, obj = args
        return obj.noneify()

class __extend__(pairtype(SomeImpossibleValue, SomeNone)):
    def union(args):
        imp1, none = args
        return s_None

class __extend__(pairtype(SomeNone, SomeImpossibleValue)):
    def union(args):
        none, imp2 = args
        return s_None


class __extend__(pairtype(SomePBC, SomeObject)):
    def getitem(args):
        pbc, o = args
        raise AnnotatorError("getitem on %r" % pbc)

    def setitem(args, s_value):
        pbc, o = args
        raise AnnotatorError("setitem on %r" % pbc)

class __extend__(pairtype(SomeNone, SomeObject)):
    def getitem(args):
        none, o = args
        return s_ImpossibleValue
    getitem.can_only_throw = []

    def setitem(args, s_value):
        none, o = args
        return None

class __extend__(pairtype(SomePBC, SomeString)):
    def add(args):
        pbc, o = args
        raise AnnotatorError('add on %r' % pbc)

class __extend__(pairtype(SomeNone, SomeString)):
    def add(args):
        none, o = args
        return s_ImpossibleValue

class __extend__(pairtype(SomeString, SomePBC)):
    def add(args):
        o, pbc = args
        raise AnnotatorError('add on %r' % pbc)

class __extend__(pairtype(SomeString, SomeNone)):
    def add(args):
        o, none = args
        return s_ImpossibleValue

#_________________________________________
# weakrefs

class __extend__(pairtype(SomeWeakRef, SomeWeakRef)):
    def union(args):
        s_wrf1, s_wrf2 = args
        if s_wrf1.classdef is None:
            basedef = s_wrf2.classdef   # s_wrf1 is known to be dead
        elif s_wrf2.classdef is None:
            basedef = s_wrf1.classdef   # s_wrf2 is known to be dead
        else:
            basedef = s_wrf1.classdef.commonbase(s_wrf2.classdef)
            if basedef is None:    # no common base class! complain...
                raise UnionError(s_wrf1, s_wrf2)
        return SomeWeakRef(basedef)
