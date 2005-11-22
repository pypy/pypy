from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem.lltype import \
     Signed, Unsigned, Bool, Float, Void
from pypy.rpython.error import TyperError
from pypy.rpython.rmodel import FloatRepr
from pypy.rpython.rmodel import IntegerRepr, BoolRepr, StringRepr
from pypy.rpython.robject import PyObjRepr, pyobj_repr
from pypy.rpython.rstr import string_repr
from pypy.rpython import rstr
from pypy.rpython.rmodel import log

import math

class __extend__(annmodel.SomeFloat):
    def rtyper_makerepr(self, rtyper):
        return float_repr
    def rtyper_makekey(self):
        return self.__class__,


float_repr = FloatRepr()


class __extend__(pairtype(FloatRepr, FloatRepr)):

    #Arithmetic

    def rtype_add(_, hop):
        return _rtype_template(hop, 'add')

    rtype_inplace_add = rtype_add

    def rtype_sub(_, hop):
        return _rtype_template(hop, 'sub')

    rtype_inplace_sub = rtype_sub

    def rtype_mul(_, hop):
        return _rtype_template(hop, 'mul')

    rtype_inplace_mul = rtype_mul

    def rtype_div(_, hop):
        # turn 'div' on floats into 'truediv'
        return _rtype_template(hop, 'truediv')

    rtype_inplace_div     = rtype_div
    rtype_truediv         = rtype_div
    rtype_inplace_truediv = rtype_div

    def rtype_pow(_, hop):
        s_float3 = hop.args_s[2]
        if s_float3.is_constant() and s_float3.const is None:
            vlist = hop.inputargs(Float, Float, Void)[:2]
            return hop.genop('float_pow', vlist, resulttype=Float)
        else:
            raise TyperError("cannot handle pow with three float arguments")

    def rtype_inplace_pow(_, hop):
        return _rtype_template(hop, 'pow')

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

class __extend__(pairtype(StringRepr, FloatRepr)):
    def rtype_mod(_, hop):
        return rstr.do_stringformat(hop, [(hop.args_v[1], hop.args_r[1])])

#Helpers FloatRepr,FloatRepr

def _rtype_template(hop, func):
    vlist = hop.inputargs(Float, Float)
    return hop.genop('float_'+func, vlist, resulttype=Float)

def _rtype_compare_template(hop, func):
    vlist = hop.inputargs(Float, Float)
    return hop.genop('float_'+func, vlist, resulttype=Bool)

#

class __extend__(FloatRepr):

    def convert_const(self, value):
        if not isinstance(value, (int, float)):  # can be bool too
            raise TyperError("not a float: %r" % (value,))
        return float(value)

    def get_ll_eq_function(self):
        return None

    def get_ll_hash_function(self):
        return ll_hash_float

    def rtype_is_true(_, hop):
        vlist = hop.inputargs(Float)
        return hop.genop('float_is_true', vlist, resulttype=Bool)

    def rtype_neg(_, hop):
        vlist = hop.inputargs(Float)
        return hop.genop('float_neg', vlist, resulttype=Float)

    def rtype_pos(_, hop):
        vlist = hop.inputargs(Float)
        return vlist[0]

    def rtype_abs(_, hop):
        vlist = hop.inputargs(Float)
        return hop.genop('float_abs', vlist, resulttype=Float)

    def rtype_int(_, hop):
        vlist = hop.inputargs(Float)
        return hop.genop('cast_float_to_int', vlist, resulttype=Signed)

    rtype_float = rtype_pos

    def ll_str(self, f):
        from pypy.rpython.module.ll_strtod import ll_strtod_formatd
        return ll_strtod_formatd(percent_f, f)

    def rtype_hash(_, hop):
        v_flt, = hop.inputargs(float_repr)
        return hop.gendirectcall(ll_hash_float, v_flt)

percent_f = string_repr.convert_const("%f")

TAKE_NEXT = float(2**31)

def ll_hash_float(f):
    """
    this implementation is identical to the CPython implementation,
    despite the fact that the integer case is not treated, specially.
    This should be special-cased in W_FloatObject.
    In the low-level case, floats cannot be used with ints in dicts, anyway.
    """
    v, expo = math.frexp(f)
    v *= TAKE_NEXT
    hipart = int(v)
    v = (v - float(hipart)) * TAKE_NEXT
    x = hipart + int(v) + (expo << 15)
    return x
#
# _________________________ Conversions _________________________

class __extend__(pairtype(IntegerRepr, FloatRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        if r_from.lowleveltype == Unsigned and r_to.lowleveltype == Float:
            log.debug('explicit cast_uint_to_float')
            return llops.genop('cast_uint_to_float', [v], resulttype=Float)
        if r_from.lowleveltype == Signed and r_to.lowleveltype == Float:
            log.debug('explicit cast_int_to_float')
            return llops.genop('cast_int_to_float', [v], resulttype=Float)
        return NotImplemented

class __extend__(pairtype(BoolRepr, FloatRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        if r_from.lowleveltype == Bool and r_to.lowleveltype == Float:
            log.debug('explicit cast_bool_to_float')
            return llops.genop('cast_bool_to_float', [v], resulttype=Float)
        return NotImplemented

class __extend__(pairtype(PyObjRepr, FloatRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        if r_to.lowleveltype == Float:
            return llops.gencapicall('PyFloat_AsDouble', [v],
                                     resulttype=Float)
        return NotImplemented

class __extend__(pairtype(FloatRepr, PyObjRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        if r_from.lowleveltype == Float:
            return llops.gencapicall('PyFloat_FromDouble', [v],
                                     resulttype=pyobj_repr)
        return NotImplemented
