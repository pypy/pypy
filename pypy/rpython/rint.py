from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.objspace import op_appendices
from pypy.rpython.lltype import Signed, Unsigned, Bool, Float, Void, Char
from pypy.rpython.rmodel import Repr, TyperError, IntegerRepr, CharRepr
from pypy.rpython.robject import PyObjRepr, pyobj_repr


debug = False

class __extend__(annmodel.SomeInteger):
    def rtyper_makerepr(self, rtyper):
        if self.unsigned:
            return unsigned_repr
        else:
            return signed_repr
    def rtyper_makekey(self):
        return self.unsigned

signed_repr = IntegerRepr()
unsigned_repr = IntegerRepr()
unsigned_repr.lowleveltype = Unsigned


class __extend__(pairtype(IntegerRepr, IntegerRepr)):

    def convert_from_to((r_from, r_to), v, llops):
        if r_from.lowleveltype == Unsigned and r_to.lowleveltype == Signed:
            if debug: print 'explicit cast_int_to_uint'
            return llops.genop('cast_int_to_uint', [v], resulttype=Unsigned)
        if r_from.lowleveltype == Signed and r_to.lowleveltype == Unsigned:
            if debug: print 'explicit cast_uint_to_int'
            return llops.genop('cast_uint_to_int', [v], resulttype=Signed)
        return v

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

    def rtype_div(_, hop):
        return _rtype_template(hop, 'div', [ZeroDivisionError])
    rtype_inplace_div = rtype_div

    def rtype_div_ovf(_, hop):
        return _rtype_template(hop, 'div_ovf', [ZeroDivisionError])

    def rtype_floordiv(_, hop):
        return _rtype_template(hop, 'floordiv', [ZeroDivisionError])
    rtype_inplace_floordiv = rtype_floordiv

    def rtype_floordiv_ovf(_, hop):
        return _rtype_template(hop, 'floordiv_ovf', [ZeroDivisionError])

    def rtype_truediv(_, hop):
        return _rtype_template(hop, 'truediv', [ZeroDivisionError])
    rtype_inplace_truediv = rtype_truediv

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
        if hop.s_result.unsigned:
            if s_int3.is_constant() and s_int3.const is None:
                vlist = hop.inputargs(Unsigned, Unsigned, Void)[:2]
            else:
                vlist = hop.inputargs(Unsigned, Unsigned, Unsigned)
            return hop.genop('uint_pow' + suffix, vlist, resulttype=Unsigned)
        else:
            if s_int3.is_constant() and s_int3.const is None:
                vlist = hop.inputargs(Signed, Signed, Void)[:2]
            else:
                vlist = hop.inputargs(Signed, Signed, Signed)
            return hop.genop('int_pow' + suffix, vlist, resulttype=Signed)

    def rtype_pow_ovf(_, hop):
        if hop.s_result.unsigned:
            raise TyperError("forbidden uint_pow_ovf")
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
    func1 = func
    for implicit_exc in implicit_excs:
        if hop.has_implicit_exception(implicit_exc):
            appendix = op_appendices[implicit_exc]
            func += '_' + appendix
    if hop.s_result.unsigned:
        if func1.endswith('_ovf'):
            raise TyperError("forbidden uint_" + func)
        vlist = hop.inputargs(Unsigned, Unsigned)
        return hop.genop('uint_'+func, vlist, resulttype=Unsigned)
    else:
        vlist = hop.inputargs(Signed, Signed)
        return hop.genop('int_'+func, vlist, resulttype=Signed)

#Helper functions for comparisons

def _rtype_compare_template(hop, func):
    s_int1, s_int2 = hop.args_s
    if s_int1.unsigned or s_int2.unsigned:
        if not s_int1.nonneg or not s_int2.nonneg:
            raise TyperError("comparing a signed and an unsigned number")
        vlist = hop.inputargs(Unsigned, Unsigned)
        return hop.genop('uint_'+func, vlist, resulttype=Bool)
    else:
        vlist = hop.inputargs(Signed, Signed)
        return hop.genop('int_'+func, vlist, resulttype=Bool)


#

class __extend__(IntegerRepr):

    def convert_const(self, value):
        if not isinstance(value, int):   # can be bool
            raise TyperError("not an integer: %r" % (value,))
        return int(value)

    def rtype_float(_, hop):
        vlist = hop.inputargs(Float)
        return vlist[0]

    def rtype_chr(_, hop):
        vlist =  hop.inputargs(Char)
        return vlist[0]

    def rtype_is_true(self, hop):
        if self.lowleveltype == Unsigned:
            vlist = hop.inputargs(Unsigned)
            return hop.genop('uint_is_true', vlist, resulttype=Bool)
        else:
            vlist = hop.inputargs(Signed)
            return hop.genop('int_is_true', vlist, resulttype=Bool)

    #Unary arithmetic operations    
    
    def rtype_abs(_, hop):
        if hop.s_result.unsigned:
            vlist = hop.inputargs(Unsigned)
            return vlist[0]
        else:
            vlist = hop.inputargs(Signed)
            return hop.genop('int_abs', vlist, resulttype=Signed)

    def rtype_abs_ovf(_, hop):
        if hop.s_result.unsigned:
            raise TyperError("forbidden uint_abs_ovf")
        else:
            vlist = hop.inputargs(Signed)
            return hop.genop('int_abs_ovf', vlist, resulttype=Signed)

    def rtype_invert(_, hop):
        if hop.s_result.unsigned:
            vlist = hop.inputargs(Unsigned)
            return hop.genop('uint_invert', vlist, resulttype=Unsigned)
        else:
            vlist = hop.inputargs(Signed)
            return hop.genop('int_invert', vlist, resulttype=Signed)

    def rtype_neg(_, hop):
        if hop.s_result.unsigned:
            vlist = hop.inputargs(Unsigned)
            return hop.genop('uint_neg', vlist, resulttype=Unsigned)
        else:
            vlist = hop.inputargs(Signed)
            return hop.genop('int_neg', vlist, resulttype=Signed)

    def rtype_neg_ovf(_, hop):
        if hop.s_result.unsigned:
            raise TyperError("forbidden uint_neg_ovf")
        else:
            vlist = hop.inputargs(Signed)
            return hop.genop('int_neg_ovf', vlist, resulttype=Signed)

    def rtype_pos(_, hop):
        if hop.s_result.unsigned:
            vlist = hop.inputargs(Unsigned)
        else:
            vlist = hop.inputargs(Signed)
        return vlist[0]

    def rtype_int(r_int, hop):
        if r_int.lowleveltype == Unsigned:
            raise TyperError("use intmask() instead of int(r_uint(...))")
        vlist = hop.inputargs(Signed)
        return vlist[0]

    def rtype_float(_, hop):
        vlist = hop.inputargs(Float)
        return vlist[0]

#
# _________________________ Conversions _________________________

class __extend__(pairtype(PyObjRepr, IntegerRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        if r_to.lowleveltype == Unsigned:
            return llops.gencapicall('PyLong_AsUnsignedLong', [v],
                                     resulttype=Unsigned)
        if r_to.lowleveltype == Signed:
            return llops.gencapicall('PyInt_AsLong', [v],
                                     resulttype=Signed)
        return NotImplemented

class __extend__(pairtype(IntegerRepr, PyObjRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        if r_from.lowleveltype == Unsigned:
            return llops.gencapicall('PyLong_FromUnsignedLong', [v],
                                     resulttype=pyobj_repr)
        if r_from.lowleveltype == Signed:
            return llops.gencapicall('PyInt_FromLong', [v],
                                     resulttype=pyobj_repr)
        return NotImplemented

class __extend__(pairtype(IntegerRepr, CharRepr)):
        def convert_from_to((r_from, r_to), v, llops):
            if r_from.lowleveltype == Signed:
                return llops.genop('cast_int_to_chr', [v], resulttype=Char)
            return NotImplemented
