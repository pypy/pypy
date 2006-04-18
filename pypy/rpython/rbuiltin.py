from pypy.annotation.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython.lltypesystem import lltype, rclass, llmemory
from pypy.rpython import rarithmetic, objectmodel, rstack, rint, raddress
from pypy.rpython.error import TyperError
from pypy.rpython.rmodel import Repr, IntegerRepr, inputconst
from pypy.rpython.rrange import rtype_builtin_range, rtype_builtin_xrange
from pypy.rpython import rstr
from pypy.rpython import rptr
from pypy.rpython.robject import pyobj_repr
from pypy.rpython.rdict import rtype_r_dict
from pypy.tool import sourcetools
from pypy.rpython import extregistry

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
            result = BuiltinMethodRepr(rtyper, self.s_self, self.methodname)
            if result.self_repr == pyobj_repr:
                return pyobj_repr   # special case: methods of 'PyObject*'
            else:
                return result
    def rtyper_makekey(self):
        if self.s_self is None:
            # built-in function case

            const = getattr(self, 'const', None)

            if extregistry.is_registered(const):
                const = extregistry.lookup(const)

            return self.__class__, const
        else:
            # built-in method case
            # NOTE: we hash by id of self.s_self here.  This appears to be
            # necessary because it ends up in hop.args_s[0] in the method call,
            # and there is no telling what information the called
            # rtype_method_xxx() will read from that hop.args_s[0].
            # See test_method_join in test_rbuiltin.
            # There is no problem with self.s_self being garbage-collected and
            # its id reused, because the BuiltinMethodRepr keeps a reference
            # to it.
            return (self.__class__, self.methodname, id(self.s_self))


class BuiltinFunctionRepr(Repr):
    lowleveltype = lltype.Void

    def __init__(self, builtinfunc):
        self.builtinfunc = builtinfunc

    def rtype_simple_call(self, hop):
        try:
            bltintyper = BUILTIN_TYPER[self.builtinfunc]
        except (KeyError, TypeError):
            try:
                rtyper = hop.rtyper
                bltintyper = rtyper.type_system.rbuiltin.\
                                    BUILTIN_TYPER[self.builtinfunc]
            except (KeyError, TypeError):
##                if hasattr(self.builtinfunc,"specialize"):
##                    bltintyper = self.builtinfunc.specialize
##                else
                if extregistry.is_registered(self.builtinfunc):
                    entry = extregistry.lookup(self.builtinfunc)
                    bltintyper = entry.specialize_call
                else:
                    raise TyperError("don't know about built-in function %r" % (
                        self.builtinfunc,))
        hop2 = hop.copy()
        hop2.r_s_popfirstarg()
        return bltintyper(hop2)

    def rtype_call_args(self, hop):
        # calling a built-in function with keyword arguments:
        # mostly for rpython.objectmodel.hint()
        from pypy.interpreter.argument import Arguments
        arguments = Arguments.fromshape(None, hop.args_s[1].const, # shape
                                        hop.args_s[2:])
        args_s, kwds = arguments.unpack()
        # prefix keyword arguments with 's_'
        kwds_s = {}
        for key, s_value in kwds.items():
            kwds_s['s_'+key] = s_value
        bltintyper = BUILTIN_TYPER[self.builtinfunc]
        hop2 = hop.copy()
        hop2.r_s_popfirstarg()
        hop2.r_s_popfirstarg()
        return bltintyper(hop2, **kwds_s)


class BuiltinMethodRepr(Repr):

    def __init__(self, rtyper, s_self, methodname):
        self.s_self = s_self
        self.self_repr = rtyper.getrepr(s_self)
        self.methodname = methodname
        # methods of a known name are implemented as just their 'self'
        self.lowleveltype = self.self_repr.lowleveltype

    def convert_const(self, obj):
        return self.self_repr.convert_const(obj.__self__)

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

class __extend__(pairtype(BuiltinMethodRepr, BuiltinMethodRepr)):
    def convert_from_to((r_from, r_to), v, llops):
        # convert between two MethodReprs only if they are about the same
        # methodname.  (Useful for the case r_from.s_self == r_to.s_self but
        # r_from is not r_to.)  See test_rbuiltin.test_method_repr.
        if r_from.methodname != r_to.methodname:
            return NotImplemented
        return llops.convertvar(v, r_from.self_repr, r_to.self_repr)

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

#def rtype_builtin_range(hop): see rrange.py

#def rtype_builtin_xrange(hop): see rrange.py

#def rtype_r_dict(hop): see rdict.py

def rtype_intmask(hop):
    hop.exception_cannot_occur()
    vlist = hop.inputargs(lltype.Signed)
    return vlist[0]

def rtype_r_uint(hop):
    vlist = hop.inputargs(lltype.Unsigned)
    return vlist[0]

def rtype_r_longlong(hop):
    vlist = hop.inputargs(lltype.SignedLongLong)
    return vlist[0]

def rtype_r_ulonglong(hop):
    vlist = hop.inputargs(lltype.UnsignedLongLong)
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

def rtype_object__init__(hop):
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

def rtype_we_are_translated(hop):
    hop.exception_cannot_occur()
    return hop.inputconst(lltype.Bool, True)

def rtype_yield_current_frame_to_caller(hop):
    return hop.genop('yield_current_frame_to_caller', [],
                     resulttype=hop.r_result)

def rtype_hlinvoke(hop):
    _, s_repr = hop.r_s_popfirstarg()
    r_callable = s_repr.const

    r_func, nimplicitarg = r_callable.get_r_implfunc()
    s_callable = r_callable.get_s_callable()

    nbargs = len(hop.args_s) - 1 + nimplicitarg 
    s_sigs = r_func.get_s_signatures((nbargs, (), False, False))
    if len(s_sigs) != 1:
        raise TyperError("cannot hlinvoke callable %r with not uniform"
                         "annotations: %r" % (r_callable,
                                              s_sigs))
    args_s, s_ret = s_sigs[0]
    rinputs = [hop.rtyper.getrepr(s_obj) for s_obj in args_s]
    rresult = hop.rtyper.getrepr(s_ret)

    args_s = args_s[nimplicitarg:]
    rinputs = rinputs[nimplicitarg:]

    new_args_r = [r_callable] + rinputs

    for i in range(len(new_args_r)):
        assert hop.args_r[i].lowleveltype == new_args_r[i].lowleveltype

    hop.args_r = new_args_r
    hop.args_s = [s_callable] + args_s

    hop.s_result = s_ret
    assert hop.r_result.lowleveltype == rresult.lowleveltype
    hop.r_result = rresult

    return hop.dispatch()


# collect all functions
import __builtin__
BUILTIN_TYPER = {}
for name, value in globals().items():
    if name.startswith('rtype_builtin_'):
        original = getattr(__builtin__, name[14:])
        BUILTIN_TYPER[original] = value
BUILTIN_TYPER[Exception.__init__.im_func] = rtype_Exception__init__
BUILTIN_TYPER[AssertionError.__init__.im_func] = rtype_Exception__init__
BUILTIN_TYPER[OSError.__init__.im_func] = rtype_OSError__init__
BUILTIN_TYPER[object.__init__] = rtype_object__init__
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
    hop.exception_cannot_occur()
    return hop.genop('cast_pointer', [v_input],    # v_type implicit in r_result
                     resulttype = hop.r_result.lowleveltype)

def rtype_direct_fieldptr(hop):
    assert isinstance(hop.args_r[0], rptr.PtrRepr)
    assert hop.args_s[1].is_constant()
    vlist = hop.inputargs(hop.args_r[0], lltype.Void)
    hop.exception_cannot_occur()
    return hop.genop('direct_fieldptr', vlist,
                     resulttype=hop.r_result.lowleveltype)

def rtype_direct_arrayitems(hop):
    assert isinstance(hop.args_r[0], rptr.PtrRepr)
    vlist = hop.inputargs(hop.args_r[0])
    hop.exception_cannot_occur()
    return hop.genop('direct_arrayitems', vlist,
                     resulttype=hop.r_result.lowleveltype)

def rtype_direct_ptradd(hop):
    assert isinstance(hop.args_r[0], rptr.PtrRepr)
    vlist = hop.inputargs(hop.args_r[0], lltype.Signed)
    hop.exception_cannot_occur()
    return hop.genop('direct_ptradd', vlist,
                     resulttype=hop.r_result.lowleveltype)

def rtype_cast_primitive(hop):
    assert hop.args_s[0].is_constant()
    TGT = hop.args_s[0].const
    # we don't want these as automatic conversions, so:
    if TGT == lltype.Char:
        hop2 = hop.copy()
        hop2.r_s_popfirstarg()
        return hop2.args_r[0].rtype_chr(hop2)
    elif TGT == lltype.UniChar:
        hop2 = hop.copy()
        hop2.r_s_popfirstarg()
        return hop2.args_r[0].rtype_unichr(hop2)
    elif hop.args_r[1] in (rstr.char_repr, rstr.unichar_repr):
        hop2 = hop.copy()
        hop2.r_s_popfirstarg()
        v = hop2.args_r[0].rtype_ord(hop2)
        return hop.llops.convertvar(v, rint.signed_repr, hop.r_result)
    return hop.inputarg(TGT, 1)

def rtype_cast_ptr_to_int(hop):
    assert isinstance(hop.args_r[0], rptr.PtrRepr)
    vlist = hop.inputargs(hop.args_r[0])
    return hop.genop('cast_ptr_to_int', vlist,
                     resulttype = lltype.Signed)

def rtype_runtime_type_info(hop):
    assert isinstance(hop.args_r[0], rptr.PtrRepr)
    vlist = hop.inputargs(hop.args_r[0])
    return hop.genop('runtime_type_info', vlist,
                 resulttype = rptr.PtrRepr(lltype.Ptr(lltype.RuntimeTypeInfo)))

BUILTIN_TYPER[lltype.malloc] = rtype_malloc
BUILTIN_TYPER[lltype.cast_primitive] = rtype_cast_primitive
BUILTIN_TYPER[lltype.cast_pointer] = rtype_cast_pointer
BUILTIN_TYPER[lltype.direct_fieldptr] = rtype_direct_fieldptr
BUILTIN_TYPER[lltype.direct_arrayitems] = rtype_direct_arrayitems
BUILTIN_TYPER[lltype.direct_ptradd] = rtype_direct_ptradd
BUILTIN_TYPER[lltype.cast_ptr_to_int] = rtype_cast_ptr_to_int
BUILTIN_TYPER[lltype.typeOf] = rtype_const_result
BUILTIN_TYPER[lltype.nullptr] = rtype_const_result
BUILTIN_TYPER[lltype.getRuntimeTypeInfo] = rtype_const_result
BUILTIN_TYPER[lltype.runtime_type_info] = rtype_runtime_type_info
BUILTIN_TYPER[rarithmetic.intmask] = rtype_intmask
BUILTIN_TYPER[rarithmetic.r_uint] = rtype_r_uint
BUILTIN_TYPER[rarithmetic.r_longlong] = rtype_r_longlong
BUILTIN_TYPER[rarithmetic.r_ulonglong] = rtype_r_ulonglong
BUILTIN_TYPER[objectmodel.r_dict] = rtype_r_dict
BUILTIN_TYPER[objectmodel.we_are_translated] = rtype_we_are_translated
BUILTIN_TYPER[rstack.yield_current_frame_to_caller] = (
    rtype_yield_current_frame_to_caller)

BUILTIN_TYPER[objectmodel.hlinvoke] = rtype_hlinvoke

from pypy.rpython import extfunctable

def make_rtype_extfunc(extfuncinfo):
    if extfuncinfo.ll_annotable:
        def rtype_extfunc(hop):
            ll_function = extfuncinfo.ll_function
            vars = hop.inputargs(*hop.args_r)
            hop.exception_is_here()
            return hop.gendirectcall(ll_function, *vars)
    else:
        def rtype_extfunc(hop):
            ll_function = extfuncinfo.ll_function
            resulttype = hop.r_result
            vars = hop.inputargs(*hop.args_r)
            hop.exception_is_here()
            return hop.llops.genexternalcall(ll_function.__name__, vars, resulttype=resulttype,
                                             _callable = ll_function)
            
    if extfuncinfo.func is not None:
        rtype_extfunc = sourcetools.func_with_new_name(rtype_extfunc,
            "rtype_extfunc_%s" % extfuncinfo.func.__name__)
    return rtype_extfunc


def update_exttable():
    """import rtyping information for external functions 
    from the extfunctable.table  into our own specific table
    """
    for func, extfuncinfo in extfunctable.table.iteritems():
        if func not in BUILTIN_TYPER:
            BUILTIN_TYPER[func] = make_rtype_extfunc(extfuncinfo)

# Note: calls to declare() may occur after rbuiltin.py is first imported.
# We must track future changes to the extfunctable.
extfunctable.table_callbacks.append(update_exttable)
update_exttable()


# _________________________________________________________________
# memory addresses

from pypy.rpython.memory import lladdress
from pypy.rpython.lltypesystem import llmemory

def rtype_raw_malloc(hop):
    v_size, = hop.inputargs(lltype.Signed)
    return hop.genop('raw_malloc', [v_size], resulttype=llmemory.Address)

def rtype_raw_free(hop):
    v_addr, = hop.inputargs(llmemory.Address)
    return hop.genop('raw_free', [v_addr])

def rtype_raw_memcopy(hop):
    v_list = hop.inputargs(llmemory.Address, llmemory.Address, lltype.Signed)
    return hop.genop('raw_memcopy', v_list)

BUILTIN_TYPER[lladdress.raw_malloc] = rtype_raw_malloc
BUILTIN_TYPER[lladdress.raw_free] = rtype_raw_free
BUILTIN_TYPER[lladdress.raw_memcopy] = rtype_raw_memcopy

def rtype_offsetof(hop):
    TYPE, field = hop.inputargs(lltype.Void, lltype.Void)
    return hop.inputconst(lltype.Signed,
                          llmemory.offsetof(TYPE.value, field.value))

BUILTIN_TYPER[llmemory.offsetof] = rtype_offsetof

# XXX this next little bit is a monstrous hack.  the Real Thing awaits
# some kind of proper GC integration
from pypy.rpython.l3interp import l3interp
#from pypy.rpython.raddress import offset_repr

def rtype_l3malloc(hop):
    v_list = hop.inputargs(lltype.Signed)
    return hop.genop("call_boehm_gc_alloc", v_list,
                     resulttype=llmemory.Address)

BUILTIN_TYPER[l3interp.malloc] = rtype_l3malloc

# _________________________________________________________________
# non-gc objects

def rtype_free_non_gc_object(hop):
    vinst, = hop.inputargs(hop.args_r[0])
    flavor = hop.args_r[0].getflavor()
    assert not flavor.startswith('gc')
    cflavor = hop.inputconst(lltype.Void, flavor)
    return hop.genop('flavored_free', [cflavor, vinst])
    
BUILTIN_TYPER[objectmodel.free_non_gc_object] = rtype_free_non_gc_object

# keepalive_until_here

def rtype_keepalive_until_here(hop):
    for v in hop.args_v:
        hop.genop('keepalive', [v], resulttype=lltype.Void)
    return hop.inputconst(lltype.Void, None)

BUILTIN_TYPER[objectmodel.keepalive_until_here] = rtype_keepalive_until_here

# hint

def rtype_hint(hop, **kwds_s):
    hints = {}
    for key, s_value in kwds_s.items():
        if not s_value.is_constant():
            raise TyperError("hint %r is not constant" % (key,))
        assert key.startswith('s_')
        hints[key[2:]] = s_value.const
    v = hop.inputarg(hop.args_r[0], arg=0)
    c_hint = hop.inputconst(lltype.Void, hints)
    return hop.genop('hint', [v, c_hint], resulttype=v.concretetype)

BUILTIN_TYPER[objectmodel.hint] = rtype_hint

def rtype_cast_ptr_to_adr(hop):
    vlist = hop.inputargs(hop.args_r[0])
    assert isinstance(vlist[0].concretetype, lltype.Ptr)
    hop.exception_cannot_occur()
    return hop.genop('cast_ptr_to_adr', vlist,
                     resulttype = llmemory.Address)

def rtype_cast_adr_to_ptr(hop):
    assert isinstance(hop.args_r[0], raddress.AddressRepr)
    adr, TYPE = hop.inputargs(hop.args_r[0], lltype.Void)
    hop.exception_cannot_occur()
    return hop.genop('cast_adr_to_ptr', [adr],
                     resulttype = TYPE.value)

def rtype_cast_adr_to_int(hop):
    assert isinstance(hop.args_r[0], raddress.AddressRepr)
    adr, = hop.inputargs(hop.args_r[0])
    hop.exception_cannot_occur()
    return hop.genop('cast_adr_to_int', [adr],
                     resulttype = lltype.Signed)

BUILTIN_TYPER[llmemory.cast_ptr_to_adr] = rtype_cast_ptr_to_adr
BUILTIN_TYPER[llmemory.cast_adr_to_ptr] = rtype_cast_adr_to_ptr
BUILTIN_TYPER[llmemory.cast_adr_to_int] = rtype_cast_adr_to_int

