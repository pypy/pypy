import sys
from pypy.tool.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.objspace import op_appendices
from pypy.rpython.lltypesystem.lltype import Signed, Unsigned, Bool, Float, \
     Void, Char, UniChar, malloc, pyobjectptr, UnsignedLongLong, \
     SignedLongLong, build_number, Number, cast_primitive, typeOf
from pypy.rpython.rmodel import IntegerRepr, inputconst
from pypy.rpython.robject import PyObjRepr, pyobj_repr
from pypy.rlib.rarithmetic import intmask, r_int, r_uint, r_ulonglong, r_longlong
from pypy.rpython.error import TyperError, MissingRTypeOperation
from pypy.rpython.rmodel import log
from pypy.rlib import objectmodel

_integer_reprs = {}
def getintegerrepr(lltype, prefix=None):
    try:
        return _integer_reprs[lltype]
    except KeyError:
        pass
    repr = _integer_reprs[lltype] = IntegerRepr(lltype, prefix)
    return repr

class __extend__(annmodel.SomeInteger):
    def rtyper_makerepr(self, rtyper):
        lltype = build_number(None, self.knowntype)
        return getintegerrepr(lltype)

    def rtyper_makekey(self):
        return self.__class__, self.knowntype

signed_repr = getintegerrepr(Signed, 'int_')
signedlonglong_repr = getintegerrepr(SignedLongLong, 'llong_')
unsigned_repr = getintegerrepr(Unsigned, 'uint_')
unsignedlonglong_repr = getintegerrepr(UnsignedLongLong, 'ullong_')


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
        return llops.genop('cast_primitive', [v], resulttype=r_to.lowleveltype)

    #arithmetic

    def rtype_add(_, hop):
        return _rtype_template(hop, 'add')
    rtype_inplace_add = rtype_add

    def rtype_add_ovf(_, hop):
        func = 'add_ovf'
        if hop.r_result.opprefix == 'int_':
            if hop.args_s[1].nonneg:
                func = 'add_nonneg_ovf'
            elif hop.args_s[0].nonneg:
                hop = hop.copy()
                hop.swap_fst_snd_args()
                func = 'add_nonneg_ovf'
        return _rtype_template(hop, func)

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

    def rtype_pow(_, hop):
        raise MissingRTypeOperation("pow(int, int)"
                                    " (use float**float instead; it is too"
                                    " easy to overlook the overflow"
                                    " issues of int**int)")

    rtype_pow_ovf = rtype_pow
    rtype_inplace_pow = rtype_pow

##    def rtype_pow(_, hop, suffix=''):
##        if hop.has_implicit_exception(ZeroDivisionError):
##            suffix += '_zer'
##        s_int3 = hop.args_s[2]
##        rresult = hop.rtyper.makerepr(hop.s_result)
##        if s_int3.is_constant() and s_int3.const is None:
##            vlist = hop.inputargs(rresult, rresult, Void)[:2]
##        else:
##            vlist = hop.inputargs(rresult, rresult, rresult)
##        hop.exception_is_here()
##        return hop.genop(rresult.opprefix + 'pow' + suffix, vlist, resulttype=rresult)

##    def rtype_pow_ovf(_, hop):
##        if hop.s_result.unsigned:
##            raise TyperError("forbidden uint_pow_ovf")
##        hop.has_implicit_exception(OverflowError) # record that we know about it
##        return self.rtype_pow(_, hop, suffix='_ovf')

##    def rtype_inplace_pow(_, hop):
##        return _rtype_template(hop, 'pow', [ZeroDivisionError])

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

    r_result = hop.r_result
    if r_result.lowleveltype == Bool:
        repr = signed_repr
    else:
        repr = r_result
    vlist = hop.inputargs(repr, repr)
    hop.exception_is_here()

    prefix = repr.opprefix

    v_res = hop.genop(prefix+func, vlist, resulttype=repr)
    bothnonneg = hop.args_s[0].nonneg and hop.args_s[1].nonneg
    if prefix in ('int_', 'llong_') and not bothnonneg:

        # cpython, and rpython, assumed that integer division truncates
        # towards -infinity.  however, in C99 and most (all?) other
        # backends, integer division truncates towards 0.  so assuming
        # that, we can generate scary code that applies the necessary
        # correction in the right cases.
        # paper and pencil are encouraged for this :)

        from pypy.rpython.rbool import bool_repr
        assert isinstance(repr.lowleveltype, Number)
        c_zero = inputconst(repr.lowleveltype, repr.lowleveltype._default)

        op = func.split('_', 1)[0]

        if op == 'floordiv':
            # return (x/y) - (((x^y)<0)&((x%y)!=0));
            v_xor = hop.genop(prefix + 'xor', vlist,
                            resulttype=repr)
            v_xor_le = hop.genop(prefix + 'le', [v_xor, c_zero],
                                 resulttype=Bool)
            v_xor_le = hop.llops.convertvar(v_xor_le, bool_repr, repr)
            v_mod = hop.genop(prefix + 'mod', vlist,
                            resulttype=repr)
            v_mod_ne = hop.genop(prefix + 'ne', [v_mod, c_zero],
                               resulttype=Bool)
            v_mod_ne = hop.llops.convertvar(v_mod_ne, bool_repr, repr)
            v_corr = hop.genop(prefix + 'and', [v_xor_le, v_mod_ne],
                             resulttype=repr)
            v_res = hop.genop(prefix + 'sub', [v_res, v_corr],
                              resulttype=repr)
        elif op == 'mod':
            # return r + y*(((x^y)<0)&(r!=0));
            v_xor = hop.genop(prefix + 'xor', vlist,
                            resulttype=repr)
            v_xor_le = hop.genop(prefix + 'le', [v_xor, c_zero],
                               resulttype=Bool)
            v_xor_le = hop.llops.convertvar(v_xor_le, bool_repr, repr)
            v_mod_ne = hop.genop(prefix + 'ne', [v_res, c_zero],
                               resulttype=Bool)
            v_mod_ne = hop.llops.convertvar(v_mod_ne, bool_repr, repr)
            v_corr1 = hop.genop(prefix + 'and', [v_xor_le, v_mod_ne],
                             resulttype=repr)
            v_corr = hop.genop(prefix + 'mul', [v_corr1, vlist[1]],
                             resulttype=repr)
            v_res = hop.genop(prefix + 'add', [v_res, v_corr],
                              resulttype=repr)
    v_res = hop.llops.convertvar(v_res, repr, r_result)
    return v_res


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
        T = typeOf(value)
        if isinstance(T, Number) or T is Bool:
            return cast_primitive(self.lowleveltype, value)
        raise TyperError("not an integer: %r" % (value,))

    def get_ll_eq_function(self):
        return None
    get_ll_gt_function = get_ll_eq_function
    get_ll_lt_function = get_ll_eq_function
    get_ll_ge_function = get_ll_eq_function
    get_ll_le_function = get_ll_eq_function

    def get_ll_ge_function(self):
        return None 

    def get_ll_hash_function(self):
        return ll_hash_int

    get_ll_fasthash_function = get_ll_hash_function

    def get_ll_dummyval_obj(self, rtyper, s_value):
        # if >= 0, then all negative values are special
        if s_value.nonneg and self.lowleveltype is Signed:
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
        vlist = hop.inputargs(self)
        if hop.s_result.unsigned:
            return vlist[0]
        else:
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
        if hop.s_result.unsigned:
            # implement '-r_uint(x)' with unsigned subtraction '0 - x'
            zero = self.lowleveltype._defl()
            vlist.insert(0, hop.inputconst(self.lowleveltype, zero))
            return hop.genop(self.opprefix + 'sub', vlist, resulttype=self)
        else:
            return hop.genop(self.opprefix + 'neg', vlist, resulttype=self)

    def rtype_neg_ovf(self, hop):
        self = self.as_int
        if hop.s_result.unsigned:
            # this is supported (and turns into just 0-x) for rbigint.py
            hop.exception_cannot_occur()
            return self.rtype_neg(hop)
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
        hop.exception_cannot_occur()
        return vlist[0]

    def rtype_float(_, hop):
        vlist = hop.inputargs(Float)
        return vlist[0]

    # version picked by specialisation based on which
    # type system rtyping is using, from <type_system>.ll_str module
    def ll_str(self, i):
        pass
    ll_str._annspecialcase_ = "specialize:ts('ll_str.ll_int_str')"

    def rtype_hex(self, hop):
        self = self.as_int
        varg = hop.inputarg(self, 0)
        true = inputconst(Bool, True)
        fn = hop.rtyper.type_system.ll_str.ll_int2hex
        return hop.gendirectcall(fn, varg, true)

    def rtype_oct(self, hop):
        self = self.as_int
        varg = hop.inputarg(self, 0)
        true = inputconst(Bool, True)
        fn = hop.rtyper.type_system.ll_str.ll_int2oct        
        return hop.gendirectcall(fn, varg, true)

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
