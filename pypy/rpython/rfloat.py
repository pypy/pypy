from pypy.tool.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.rpython.lltypesystem.lltype import (
    Signed, Unsigned, SignedLongLong, UnsignedLongLong,
    Bool, Float, Void, pyobjectptr)
from pypy.rpython.error import TyperError
from pypy.rpython.rmodel import FloatRepr
from pypy.rpython.rmodel import IntegerRepr, BoolRepr
from pypy.rpython.rstr import AbstractStringRepr
from pypy.rpython.robject import PyObjRepr, pyobj_repr
from pypy.rpython.rmodel import log

from pypy.rlib.rarithmetic import base_int
from pypy.rlib.objectmodel import _hash_float

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

    def rtype_truediv(_, hop):
        return _rtype_template(hop, 'truediv')

    rtype_inplace_truediv = rtype_truediv

    # turn 'div' on floats into 'truediv'
    rtype_div         = rtype_truediv
    rtype_inplace_div = rtype_inplace_truediv

    # 'floordiv' on floats not supported in RPython

    # pow on floats not supported in RPython

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

class __extend__(pairtype(AbstractStringRepr, FloatRepr)):
    def rtype_mod(_, hop):
        rstr = hop.rtyper.type_system.rstr
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
        if not isinstance(value, (int, base_int, float)):  # can be bool too
            raise TyperError("not a float: %r" % (value,))
        return float(value)

    def get_ll_eq_function(self):
        return None
    get_ll_gt_function = get_ll_eq_function
    get_ll_lt_function = get_ll_eq_function
    get_ll_ge_function = get_ll_eq_function
    get_ll_le_function = get_ll_eq_function

    def get_ll_hash_function(self):
        return _hash_float

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
        # int(x) never raises in RPython, you need to use
        # rarithmetic.ovfcheck_float_to_int() if you want this
        hop.exception_cannot_occur()
        return hop.genop('cast_float_to_int', vlist, resulttype=Signed)

    rtype_float = rtype_pos

    # version picked by specialisation based on which
    # type system rtyping is using, from <type_system>.ll_str module
    def ll_str(self, f):
        pass
    ll_str._annspecialcase_ = "specialize:ts('ll_str.ll_float_str')"

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
        if r_from.lowleveltype == SignedLongLong and r_to.lowleveltype == Float:
            log.debug('explicit cast_longlong_to_float')
            return llops.genop('cast_longlong_to_float', [v], resulttype=Float)
        if r_from.lowleveltype == UnsignedLongLong and r_to.lowleveltype == Float:
            log.debug('explicit cast_ulonglong_to_float')
            return llops.genop('cast_ulonglong_to_float', [v], resulttype=Float)
        return NotImplemented

class __extend__(pairtype(FloatRepr, IntegerRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        if r_from.lowleveltype == Float and r_to.lowleveltype == Unsigned:
            log.debug('explicit cast_float_to_uint')
            return llops.genop('cast_float_to_uint', [v], resulttype=Unsigned)
        if r_from.lowleveltype == Float and r_to.lowleveltype == Signed:
            log.debug('explicit cast_float_to_int')
            return llops.genop('cast_float_to_int', [v], resulttype=Signed)
        if r_from.lowleveltype == Float and r_to.lowleveltype == SignedLongLong:
            log.debug('explicit cast_float_to_longlong')
            return llops.genop('cast_float_to_longlong', [v], resulttype=SignedLongLong)
        if r_from.lowleveltype == Float and r_to.lowleveltype == UnsignedLongLong:
            log.debug('explicit cast_float_to_ulonglong')
            return llops.genop('cast_float_to_ulonglong', [v], resulttype=UnsignedLongLong)
        return NotImplemented

class __extend__(pairtype(BoolRepr, FloatRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        if r_from.lowleveltype == Bool and r_to.lowleveltype == Float:
            log.debug('explicit cast_bool_to_float')
            return llops.genop('cast_bool_to_float', [v], resulttype=Float)
        return NotImplemented

class __extend__(pairtype(FloatRepr, BoolRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        if r_from.lowleveltype == Float and r_to.lowleveltype == Bool:
            log.debug('explicit cast_float_to_bool')
            return llops.genop('float_is_true', [v], resulttype=Bool)
        return NotImplemented

class __extend__(pairtype(PyObjRepr, FloatRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        if r_to.lowleveltype == Float:
            return llops.gencapicall('PyFloat_AsDouble', [v],
                                     resulttype=Float,
                                   _callable=lambda pyo: float(pyo._obj.value))
        return NotImplemented

class __extend__(pairtype(FloatRepr, PyObjRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        if r_from.lowleveltype == Float:
            return llops.gencapicall('PyFloat_FromDouble', [v],
                                     resulttype=pyobj_repr,
                                     _callable=lambda x: pyobjectptr(x))
        return NotImplemented

# ______________________________________________________________________
# Support for r_singlefloat and r_longfloat from pypy.rlib.rarithmetic

from pypy.rpython.lltypesystem import lltype
from pypy.rpython.rmodel import Repr

class __extend__(annmodel.SomeSingleFloat):
    def rtyper_makerepr(self, rtyper):
        return SingleFloatRepr()
    def rtyper_makekey(self):
        return self.__class__,

class SingleFloatRepr(Repr):
    lowleveltype = lltype.SingleFloat

    def rtype_float(self, hop):
        v, = hop.inputargs(lltype.SingleFloat)
        hop.exception_cannot_occur()
        # we use cast_primitive to go between Float and SingleFloat.
        return hop.genop('cast_primitive', [v],
                         resulttype = lltype.Float)

class __extend__(annmodel.SomeLongFloat):
    def rtyper_makerepr(self, rtyper):
        return LongFloatRepr()
    def rtyper_makekey(self):
        return self.__class__,

class LongFloatRepr(Repr):
    lowleveltype = lltype.LongFloat

    def rtype_float(self, hop):
        v, = hop.inputargs(lltype.LongFloat)
        hop.exception_cannot_occur()
        # we use cast_primitive to go between Float and LongFloat.
        return hop.genop('cast_primitive', [v],
                         resulttype = lltype.Float)
