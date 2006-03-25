import sys
from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.objspace import op_appendices
from pypy.rpython.lltypesystem.lltype import Signed, Unsigned, Bool, Float, \
     Void, Char, UniChar, GcArray, malloc, Array, pyobjectptr, \
     UnsignedLongLong, SignedLongLong
from pypy.rpython.rmodel import IntegerRepr, inputconst
from pypy.rpython.robject import PyObjRepr, pyobj_repr
from pypy.rpython.rarithmetic import intmask, r_int, r_uint, r_ulonglong, r_longlong
from pypy.rpython.error import TyperError
from pypy.rpython.rmodel import log
from pypy.rpython import objectmodel


class __extend__(annmodel.SomeInteger):
    def rtyper_makerepr(self, rtyper):
        if self.unsigned:
            if self.size == 2:
                return unsignedlonglong_repr
            else:
                assert self.size == 1
                return unsigned_repr
        else:
            if self.size == 2:
                return signedlonglong_repr
            else:
                assert self.size == 1
                return signed_repr
    def rtyper_makekey(self):
        return self.__class__, self.unsigned, self.size

signed_repr = IntegerRepr(Signed, 'int_')
signedlonglong_repr = IntegerRepr(SignedLongLong, 'llong_')
unsigned_repr = IntegerRepr(Unsigned, 'uint_')
unsignedlonglong_repr = IntegerRepr(UnsignedLongLong, 'ullong_')


class __extend__(pairtype(IntegerRepr, IntegerRepr)):

    def convert_from_to((r_from, r_to), v, llops):
        if r_from.lowleveltype == Signed and r_to.lowleveltype == Unsigned:
            log.debug('explicit cast_int_to_uint')
            return llops.genop('cast_int_to_uint', [v], resulttype=Unsigned)
        if r_from.lowleveltype == Unsigned and r_to.lowleveltype == Signed:
            log.debug('explicit cast_uint_to_int')
            return llops.genop('cast_uint_to_int', [v], resulttype=Signed)
        if r_from.lowleveltype == Signed and r_to.lowleveltype == SignedLongLong:
            return llops.genop('cast_int_to_longlong', [v], resulttype=SignedLongLong)
        if r_from.lowleveltype == SignedLongLong and r_to.lowleveltype == Signed:
            return llops.genop('truncate_longlong_to_int', [v], resulttype=Signed)
        return NotImplemented

    #arithmetic

    def rtype_add(_, hop):
        return _rtype_template(hop, 'add')
    rtype_inplace_add = rtype_add

    def rtype_add_ovf(_, hop):
        return _rtype_template(hop, 'add_ovf')

    def rtype_sub(_, hop):
        return _rtype_template(hop, 'sub')
    rtype_inplace_sub = rtype_sub

    def rtype_sub_ovf(_, hop):
        return _rtype_template(hop, 'sub_ovf')

    def rtype_mul(_, hop):
        return _rtype_template(hop, 'mul')
    rtype_inplace_mul = rtype_mul

    def rtype_mul_ovf(_, hop):
        return _rtype_template(hop, 'mul_ovf')

    def rtype_floordiv(_, hop):
        return _rtype_template(hop, 'floordiv', [ZeroDivisionError])
    rtype_inplace_floordiv = rtype_floordiv

    def rtype_floordiv_ovf(_, hop):
        return _rtype_template(hop, 'floordiv_ovf', [ZeroDivisionError])

    # turn 'div' on integers into 'floordiv'
    rtype_div         = rtype_floordiv
    rtype_inplace_div = rtype_inplace_floordiv
    rtype_div_ovf     = rtype_floordiv_ovf

    # 'def rtype_truediv' is delegated to the superclass FloatRepr

    def rtype_mod(_, hop):
        return _rtype_template(hop, 'mod', [ZeroDivisionError])
    rtype_inplace_mod = rtype_mod

    def rtype_mod_ovf(_, hop):
        return _rtype_template(hop, 'mod_ovf', [ZeroDivisionError])

    def rtype_xor(_, hop):
        return _rtype_template(hop, 'xor')
    rtype_inplace_xor = rtype_xor

    def rtype_and_(_, hop):
        return _rtype_template(hop, 'and')
    rtype_inplace_and = rtype_and_

    def rtype_or_(_, hop):
        return _rtype_template(hop, 'or')
    rtype_inplace_or = rtype_or_

    def rtype_lshift(_, hop):
        return _rtype_template(hop, 'lshift', [ValueError])
    rtype_inplace_lshift = rtype_lshift

    def rtype_lshift_ovf(_, hop):
        return _rtype_template(hop, 'lshift_ovf', [ValueError])

    def rtype_rshift(_, hop):
        return _rtype_template(hop, 'rshift', [ValueError])
    rtype_inplace_rshift = rtype_rshift

    def rtype_pow(_, hop, suffix=''):
        if hop.has_implicit_exception(ZeroDivisionError):
            suffix += '_zer'
        s_int3 = hop.args_s[2]
        rresult = hop.rtyper.makerepr(hop.s_result)
        if s_int3.is_constant() and s_int3.const is None:
            vlist = hop.inputargs(rresult, rresult, Void)[:2]
        else:
            vlist = hop.inputargs(rresult, rresult, rresult)
        hop.exception_is_here()
        return hop.genop(rresult.opprefix + 'pow' + suffix, vlist, resulttype=rresult)

    def rtype_pow_ovf(_, hop):
        if hop.s_result.unsigned:
            raise TyperError("forbidden uint_pow_ovf")
        hop.has_implicit_exception(OverflowError) # record that we know about it
        return self.rtype_pow(_, hop, suffix='_ovf')

    def rtype_inplace_pow(_, hop):
        return _rtype_template(hop, 'pow', [ZeroDivisionError])

    #comparisons: eq is_ ne lt le gt ge

    def rtype_eq(_, hop): 
        return _rtype_compare_template(hop, 'eq')

    rtype_is_ = rtype_eq

    def rtype_ne(_, hop):
        return _rtype_compare_template(hop, 'ne')

    def rtype_lt(_, hop):
        return _rtype_compare_template(hop, 'lt')

    def rtype_le(_, hop):
        return _rtype_compare_template(hop, 'le')

    def rtype_gt(_, hop):
        return _rtype_compare_template(hop, 'gt')

    def rtype_ge(_, hop):
        return _rtype_compare_template(hop, 'ge')

#Helper functions

def _rtype_template(hop, func, implicit_excs=[]):
    if func.endswith('_ovf'):
        if hop.s_result.unsigned:
            raise TyperError("forbidden unsigned " + func)
        else:
            hop.has_implicit_exception(OverflowError)

    for implicit_exc in implicit_excs:
        if hop.has_implicit_exception(implicit_exc):
            appendix = op_appendices[implicit_exc]
            func += '_' + appendix

    repr = hop.rtyper.makerepr(hop.s_result)
    vlist = hop.inputargs(repr, repr)
    hop.exception_is_here()
    return hop.genop(repr.opprefix+func, vlist, resulttype=repr)
    

#Helper functions for comparisons

def _rtype_compare_template(hop, func):
    s_int1, s_int2 = hop.args_s
    if s_int1.unsigned or s_int2.unsigned:
        if not s_int1.nonneg or not s_int2.nonneg:
            raise TyperError("comparing a signed and an unsigned number")

    repr = hop.rtyper.makerepr(annmodel.unionof(s_int1, s_int2)).as_int
    vlist = hop.inputargs(repr, repr)
    hop.exception_is_here()
    return hop.genop(repr.opprefix+func, vlist, resulttype=Bool)


#

class __extend__(IntegerRepr):

    def convert_const(self, value):
        if isinstance(value, objectmodel.Symbolic):
            return value
        if not isinstance(value, (int, r_uint, r_int, r_longlong, r_ulonglong)):   # can be bool
            raise TyperError("not an integer: %r" % (value,))
        if self.lowleveltype == Signed:
            return intmask(value)
        if self.lowleveltype == Unsigned:
            return r_uint(value)
        if self.lowleveltype == UnsignedLongLong:
            return r_ulonglong(value)
        if self.lowleveltype == SignedLongLong:
            return r_longlong(value)
        raise NotImplementedError

    def get_ll_eq_function(self):
        return None 

    def get_ll_hash_function(self):
        return ll_hash_int

    get_ll_fasthash_function = get_ll_hash_function

    def get_ll_dummyval_obj(self, rtyper, s_value):
        # if >= 0, then all negative values are special
        if s_value.nonneg and not s_value.unsigned:
            return signed_repr    # whose ll_dummy_value is -1
        else:
            return None

    ll_dummy_value = -1

    def rtype_chr(_, hop):
        vlist =  hop.inputargs(Signed)
        if hop.has_implicit_exception(ValueError):
            hop.exception_is_here()
            hop.gendirectcall(ll_check_chr, vlist[0])
        return hop.genop('cast_int_to_char', vlist, resulttype=Char)

    def rtype_unichr(_, hop):
        vlist = hop.inputargs(Signed)
        if hop.has_implicit_exception(ValueError):
            hop.exception_is_here()
            hop.gendirectcall(ll_check_unichr, vlist[0])
        return hop.genop('cast_int_to_unichar', vlist, resulttype=UniChar)

    def rtype_is_true(self, hop):
        assert self is self.as_int   # rtype_is_true() is overridden in BoolRepr
        vlist = hop.inputargs(self)
        return hop.genop(self.opprefix + 'is_true', vlist, resulttype=Bool)

    #Unary arithmetic operations    
    
    def rtype_abs(self, hop):
        self = self.as_int
        if hop.s_result.unsigned:
            vlist = hop.inputargs(self)
            return vlist[0]
        else:
            vlist = hop.inputargs(self)
            return hop.genop(self.opprefix + 'abs', vlist, resulttype=self)

    def rtype_abs_ovf(self, hop):
        self = self.as_int
        if hop.s_result.unsigned:
            raise TyperError("forbidden uint_abs_ovf")
        else:
            vlist = hop.inputargs(self)
            hop.has_implicit_exception(OverflowError) # record we know about it
            hop.exception_is_here()
            return hop.genop(self.opprefix + 'abs_ovf', vlist, resulttype=self)

    def rtype_invert(self, hop):
        self = self.as_int
        vlist = hop.inputargs(self)
        return hop.genop(self.opprefix + 'invert', vlist, resulttype=self)
        
    def rtype_neg(self, hop):
        self = self.as_int
        vlist = hop.inputargs(self)
        return hop.genop(self.opprefix + 'neg', vlist, resulttype=self)

    def rtype_neg_ovf(self, hop):
        self = self.as_int
        if hop.s_result.unsigned:
            raise TyperError("forbidden uint_neg_ovf")
        else:
            vlist = hop.inputargs(self)
            hop.has_implicit_exception(OverflowError) # record we know about it
            hop.exception_is_here()
            return hop.genop(self.opprefix + 'neg_ovf', vlist, resulttype=self)

    def rtype_pos(self, hop):
        self = self.as_int
        vlist = hop.inputargs(self)
        return vlist[0]

    def rtype_int(self, hop):
        if self.lowleveltype in (Unsigned, UnsignedLongLong):
            raise TyperError("use intmask() instead of int(r_uint(...))")
        vlist = hop.inputargs(Signed)
        return vlist[0]

    def rtype_float(_, hop):
        vlist = hop.inputargs(Float)
        return vlist[0]

    def ll_str(self, i):
        from pypy.rpython.rstr import STR
        temp = malloc(CHAR_ARRAY, 20)
        len = 0
        sign = 0
        if i < 0:
            sign = 1
            i = r_uint(-i)
        else:
            i = r_uint(i)
        if i == 0:
            len = 1
            temp[0] = '0'
        else:
            while i:
                temp[len] = chr(i%10+ord('0'))
                i //= 10
                len += 1
        len += sign
        result = malloc(STR, len)
        if sign:
            result.chars[0] = '-'
            j = 1
        else:
            j = 0
        while j < len:
            result.chars[j] = temp[len-j-1]
            j += 1
        return result

    def rtype_hex(self, hop):
        self = self.as_int
        varg = hop.inputarg(self, 0)
        true = inputconst(Bool, True)
        return hop.gendirectcall(ll_int2hex, varg, true)

    def rtype_oct(self, hop):
        self = self.as_int
        varg = hop.inputarg(self, 0)
        true = inputconst(Bool, True)
        return hop.gendirectcall(ll_int2oct, varg, true)



CHAR_ARRAY = GcArray(Char)

hex_chars = malloc(Array(Char), 16, immortal=True)

for i in range(16):
    hex_chars[i] = "%x"%i

def ll_int2hex(i, addPrefix):
    from pypy.rpython.rstr import STR
    temp = malloc(CHAR_ARRAY, 20)
    len = 0
    sign = 0
    if i < 0:
        sign = 1
        i = -i
    if i == 0:
        len = 1
        temp[0] = '0'
    else:
        while i:
            temp[len] = hex_chars[i%16]
            i //= 16
            len += 1
    len += sign
    if addPrefix:
        len += 2
    result = malloc(STR, len)
    j = 0
    if sign:
        result.chars[0] = '-'
        j = 1
    if addPrefix:
        result.chars[j] = '0'
        result.chars[j+1] = 'x'
        j += 2
    while j < len:
        result.chars[j] = temp[len-j-1]
        j += 1
    return result

def ll_int2oct(i, addPrefix):
    from pypy.rpython.rstr import STR
    if i == 0:
        result = malloc(STR, 1)
        result.chars[0] = '0'
        return result
    temp = malloc(CHAR_ARRAY, 25)
    len = 0
    sign = 0
    if i < 0:
        sign = 1
        i = -i
    while i:
        temp[len] = hex_chars[i%8]
        i //= 8
        len += 1
    len += sign
    if addPrefix:
        len += 1
    result = malloc(STR, len)
    j = 0
    if sign:
        result.chars[0] = '-'
        j = 1
    if addPrefix:
        result.chars[j] = '0'
        j += 1
    while j < len:
        result.chars[j] = temp[len-j-1]
        j += 1
    return result

def ll_identity(n):
    return n

ll_hash_int = ll_identity

def ll_check_chr(n):
    if 0 <= n <= 255:
        return
    else:
        raise ValueError

def ll_check_unichr(n):
    if 0 <= n <= sys.maxunicode:
        return
    else:
        raise ValueError

#
# _________________________ Conversions _________________________


py_to_ll_conversion_functions = {
    UnsignedLongLong: ('RPyLong_AsUnsignedLongLong', lambda pyo: r_ulonglong(pyo._obj.value)),
    SignedLongLong: ('RPyLong_AsLongLong', lambda pyo: r_longlong(pyo._obj.value)),
    Unsigned: ('RPyLong_AsUnsignedLong', lambda pyo: r_uint(pyo._obj.value)),
    Signed: ('PyInt_AsLong', lambda pyo: int(pyo._obj.value))
}

ll_to_py_conversion_functions = {
    UnsignedLongLong: ('PyLong_FromUnsignedLongLong', lambda i: pyobjectptr(i)),
    SignedLongLong: ('PyLong_FromLongLong', lambda i: pyobjectptr(i)),
    Unsigned: ('PyLong_FromUnsignedLong', lambda i: pyobjectptr(i)),
    Signed: ('PyInt_FromLong', lambda i: pyobjectptr(i)),
}
    

class __extend__(pairtype(PyObjRepr, IntegerRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        tolltype = r_to.lowleveltype
        fnname, callable = py_to_ll_conversion_functions[tolltype]
        return llops.gencapicall(fnname, [v],
                                 resulttype=r_to, _callable=callable)

class __extend__(pairtype(IntegerRepr, PyObjRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        fromlltype = r_from.lowleveltype
        fnname, callable = ll_to_py_conversion_functions[fromlltype]
        return llops.gencapicall(fnname, [v],
                                 resulttype=pyobj_repr, _callable=callable)
