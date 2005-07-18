from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.rpython import lltype
from pypy.rpython import rarithmetic, objectmodel
from pypy.rpython.rtyper import TyperError
from pypy.rpython.rrange import rtype_builtin_range, rtype_builtin_xrange 
from pypy.rpython.rmodel import Repr, TyperError, IntegerRepr, Constant
from pypy.rpython import rptr
from pypy.rpython.robject import pyobj_repr
from pypy.rpython.rfloat import float_repr, FloatRepr
from pypy.rpython.rbool import bool_repr
from pypy.rpython import rclass
from pypy.tool import sourcetools

class __extend__(annmodel.SomeBuiltin):
    def rtyper_makerepr(self, rtyper):
        if self.s_self is None:
            # built-in function case
            if not self.is_constant():
                raise TyperError("non-constant built-in function!")
            return BuiltinFunctionRepr(self.const)
        else:
            # built-in method case
            assert self.methodname is not None
            return BuiltinMethodRepr(rtyper, self.s_self, self.methodname)
    def rtyper_makekey(self):
        if self.s_self is None:
            # built-in function case
            return getattr(self, 'const', None)
        else:
            # built-in method case
            return (self.methodname, self.s_self.rtyper_makekey())


class BuiltinFunctionRepr(Repr):
    lowleveltype = lltype.Void

    def __init__(self, builtinfunc):
        self.builtinfunc = builtinfunc

    def rtype_simple_call(self, hop):
        try:
            bltintyper = BUILTIN_TYPER[self.builtinfunc]
        except KeyError:
            raise TyperError("don't know about built-in function %r" % (
                self.builtinfunc,))
        hop2 = hop.copy()
        hop2.r_s_popfirstarg()
        return bltintyper(hop2)


class BuiltinMethodRepr(Repr):

    def __init__(self, rtyper, s_self, methodname):
        self.s_self = s_self
        self.self_repr = rtyper.getrepr(s_self)
        self.methodname = methodname
        # methods of a known name are implemented as just their 'self'
        self.lowleveltype = self.self_repr.lowleveltype

    def rtype_simple_call(self, hop):
        # methods: look up the rtype_method_xxx()
        name = 'rtype_method_' + self.methodname
        try:
            bltintyper = getattr(self.self_repr, name)
        except AttributeError:
            raise TyperError("missing %s.%s" % (
                self.self_repr.__class__.__name__, name))
        # hack based on the fact that 'lowleveltype == self_repr.lowleveltype'
        hop2 = hop.copy()
        assert hop2.args_r[0] is self
        if isinstance(hop2.args_v[0], Constant):
            c = hop2.args_v[0].value    # get object from bound method
            hop2.args_v[0] = Constant(c.__self__)
        hop2.args_s[0] = self.s_self
        hop2.args_r[0] = self.self_repr
        return bltintyper(hop2)


##class __extend__(pairtype(SomeBuiltin, SomeObject)):

##    def rtype_convert_from_to((s_blt, s_to), v, llops):
##        if s_blt.s_self is None:
##            raise TyperError("conversion requested on a built-in function")
##        return llops.convertvar(v, s_blt.s_self, s_to)

# ____________________________________________________________

def rtype_builtin_bool(hop):
    assert hop.nb_args == 1
    return hop.args_r[0].rtype_is_true(hop)

def rtype_builtin_int(hop):
    if isinstance(hop.args_s[0], annmodel.SomeString):
	assert 1 <= hop.nb_args <= 2
	return hop.args_r[0].rtype_int(hop)
    assert hop.nb_args == 1
    return hop.args_r[0].rtype_int(hop)

def rtype_builtin_float(hop):
    assert hop.nb_args == 1
    return hop.args_r[0].rtype_float(hop)

def rtype_builtin_chr(hop):
    assert hop.nb_args == 1
    return hop.args_r[0].rtype_chr(hop)

def rtype_builtin_unichr(hop):
    assert hop.nb_args == 1
    return hop.args_r[0].rtype_unichr(hop)

def rtype_builtin_list(hop):
    return hop.args_r[0].rtype_bltn_list(hop)

def rtype_builtin_isinstance(hop):
    if hop.args_r[0] == pyobj_repr or hop.args_r[1] == pyobj_repr:
        v_obj, v_typ = hop.inputargs(pyobj_repr, pyobj_repr)
        c = hop.inputconst(pyobj_repr, isinstance)
        v = hop.genop('simple_call', [c, v_obj, v_typ], resulttype = pyobj_repr)
        return hop.llops.convertvar(v, pyobj_repr, bool_repr)        
    
    instance_repr = rclass.getinstancerepr(hop.rtyper, None)
    class_repr = rclass.get_type_repr(hop.rtyper)
    
    v_obj, v_cls = hop.inputargs(instance_repr, class_repr)

    return hop.gendirectcall(rclass.ll_isinstance, v_obj, v_cls)

#def rtype_builtin_range(hop): see rrange.py

#def rtype_builtin_xrange(hop): see rrange.py

def rtype_intmask(hop):
    vlist = hop.inputargs(lltype.Signed)
    return vlist[0]

def rtype_r_uint(hop):
    vlist = hop.inputargs(lltype.Unsigned)
    return vlist[0]

def rtype_builtin_min(hop):
    rint1, rint2 = hop.args_r
    assert isinstance(rint1, IntegerRepr)
    assert isinstance(rint2, IntegerRepr)
    assert rint1.lowleveltype == rint2.lowleveltype
    v1, v2 = hop.inputargs(rint1, rint2)
    return hop.gendirectcall(ll_min, v1, v2)

def ll_min(i1, i2):
    if i1 < i2:
        return i1
    return i2

def rtype_builtin_max(hop):
    rint1, rint2 = hop.args_r
    assert isinstance(rint1, IntegerRepr)
    assert isinstance(rint2, IntegerRepr)
    assert rint1.lowleveltype == rint2.lowleveltype
    v1, v2 = hop.inputargs(rint1, rint2)
    return hop.gendirectcall(ll_max, v1, v2)

def ll_max(i1, i2):
    if i1 > i2:
        return i1
    return i2

def rtype_Exception__init__(hop):
    pass

def rtype_OSError__init__(hop):
    if hop.nb_args == 2:
        raise TyperError("OSError() should not be called with "
                         "a single argument")
    if hop.nb_args >= 3:
        v_self = hop.args_v[0]
        r_self = hop.args_r[0]
        v_errno = hop.inputarg(lltype.Signed, arg=1)
        r_self.setfield(v_self, 'errno', v_errno, hop.llops)

def rtype_math_floor(hop):
    vlist = hop.inputargs(lltype.Float)
    return hop.genop('float_floor', vlist, resulttype=lltype.Float)

def rtype_math_fmod(hop):
    vlist = hop.inputargs(lltype.Float, lltype.Float)
    return hop.genop('float_fmod', vlist, resulttype=lltype.Float)

def ll_instantiate(typeptr, RESULT):
    my_instantiate = typeptr.instantiate
    return lltype.cast_pointer(RESULT, my_instantiate())

def rtype_instantiate(hop):
    s_class = hop.args_s[0]
    assert isinstance(s_class, annmodel.SomePBC)
    if len(s_class.prebuiltinstances) != 1:
        # instantiate() on a variable class
        vtypeptr, = hop.inputargs(rclass.get_type_repr(hop.rtyper))
        cresult = hop.inputconst(lltype.Void, hop.r_result.lowleveltype)
        return hop.gendirectcall(ll_instantiate, vtypeptr, cresult)

    klass = s_class.const
    return rclass.rtype_new_instance(hop.rtyper, klass, hop.llops)


import math
##def ll_floor(f1):
##    return float(int((f1)

# collect all functions
import __builtin__
BUILTIN_TYPER = {}
for name, value in globals().items():
    if name.startswith('rtype_builtin_'):
        original = getattr(__builtin__, name[14:])
        BUILTIN_TYPER[original] = value
BUILTIN_TYPER[math.floor] = rtype_math_floor
BUILTIN_TYPER[math.fmod] = rtype_math_fmod
BUILTIN_TYPER[Exception.__init__.im_func] = rtype_Exception__init__
BUILTIN_TYPER[AssertionError.__init__.im_func] = rtype_Exception__init__
BUILTIN_TYPER[OSError.__init__.im_func] = rtype_OSError__init__
# annotation of low-level types

def rtype_malloc(hop):
    assert hop.args_s[0].is_constant()
    if hop.nb_args == 1:
        vlist = hop.inputargs(lltype.Void)
        return hop.genop('malloc', vlist,
                         resulttype = hop.r_result.lowleveltype)
    else:
        vlist = hop.inputargs(lltype.Void, lltype.Signed)
        return hop.genop('malloc_varsize', vlist,
                         resulttype = hop.r_result.lowleveltype)

def rtype_const_result(hop):
    return hop.inputconst(hop.r_result.lowleveltype, hop.s_result.const)

def rtype_cast_pointer(hop):
    assert hop.args_s[0].is_constant()
    assert isinstance(hop.args_r[1], rptr.PtrRepr)
    v_type, v_input = hop.inputargs(lltype.Void, hop.args_r[1])
    return hop.genop('cast_pointer', [v_input],    # v_type implicit in r_result
                     resulttype = hop.r_result.lowleveltype)

def rtype_runtime_type_info(hop):
    assert isinstance(hop.args_r[0], rptr.PtrRepr)
    vlist = hop.inputargs(hop.args_r[0])
    return hop.genop('runtime_type_info', vlist,
                 resulttype = rptr.PtrRepr(lltype.Ptr(lltype.RuntimeTypeInfo)))


BUILTIN_TYPER[lltype.malloc] = rtype_malloc
BUILTIN_TYPER[lltype.cast_pointer] = rtype_cast_pointer
BUILTIN_TYPER[lltype.typeOf] = rtype_const_result
BUILTIN_TYPER[lltype.nullptr] = rtype_const_result
BUILTIN_TYPER[lltype.getRuntimeTypeInfo] = rtype_const_result
BUILTIN_TYPER[lltype.runtime_type_info] = rtype_runtime_type_info
BUILTIN_TYPER[rarithmetic.intmask] = rtype_intmask
BUILTIN_TYPER[rarithmetic.r_uint] = rtype_r_uint
BUILTIN_TYPER[objectmodel.instantiate] = rtype_instantiate

import time

def rtype_time_clock(hop):
    c = hop.inputconst(pyobj_repr, time.clock)
    v = hop.genop('simple_call', [c], resulttype = pyobj_repr)
    return hop.llops.convertvar(v, pyobj_repr, float_repr)

BUILTIN_TYPER[time.clock] = rtype_time_clock


def rtype_time_time(hop):
    c = hop.inputconst(pyobj_repr, time.time)
    v = hop.genop('simple_call', [c], resulttype = pyobj_repr)
    return hop.llops.convertvar(v, pyobj_repr, float_repr)

BUILTIN_TYPER[time.time] = rtype_time_time
    
import math

def rtype_math_exp(hop):
    vlist = hop.inputargs(lltype.Float)
    # XXX need PyFPE_START_PROTECT/PyFPE_END_PROTECT/Py_SET_ERRNO_ON_MATH_ERROR
    return hop.llops.gencapicall('exp', vlist, resulttype=lltype.Float,
                                 includes=("math.h",))   # XXX clean up needed

BUILTIN_TYPER[math.exp] = rtype_math_exp

from pypy.rpython import extfunctable

def make_rtype_extfunc(extfuncinfo):
    ll_function = extfuncinfo.ll_function
    if extfuncinfo.ll_annotable:
        def rtype_extfunc(hop):
            vars = hop.inputargs(*hop.args_r)
            return hop.gendirectcall(ll_function, *vars)
    else:
        def rtype_extfunc(hop):
            resulttype = hop.r_result
            vars = hop.inputargs(*hop.args_r)
            return hop.llops.genexternalcall(ll_function.__name__, vars, resulttype=resulttype,
                                             _callable = ll_function)
            
    return sourcetools.func_with_new_name(rtype_extfunc,
                                          "rtype_extfunc_%s" % extfuncinfo.func.__name__)

# import rtyping information for external functions 
# from the extfunctable.table  into our own specific table 
for func, extfuncinfo in extfunctable.table.iteritems():
    BUILTIN_TYPER[func] = make_rtype_extfunc(extfuncinfo)

