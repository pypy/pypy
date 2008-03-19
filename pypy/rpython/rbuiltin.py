from pypy.tool.pairtype import pairtype
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython.lltypesystem import lltype, rclass, llmemory
from pypy.rpython import rint, raddress
from pypy.rlib import rarithmetic, objectmodel
from pypy.rpython.error import TyperError
from pypy.rpython.rmodel import Repr, IntegerRepr, inputconst
from pypy.rpython.rrange import rtype_builtin_range, rtype_builtin_xrange
from pypy.rpython import rstr
from pypy.rpython import rptr
from pypy.rpython.robject import pyobj_repr
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

def call_args_expand(hop, takes_kwds = True):
    hop = hop.copy()
    from pypy.interpreter.argument import Arguments
    arguments = Arguments.fromshape(None, hop.args_s[1].const, # shape
                                    range(hop.nb_args-2))
    if arguments.w_starstararg is not None:
        raise TyperError("**kwds call not implemented")
    if arguments.w_stararg is not None:
        # expand the *arg in-place -- it must be a tuple
        from pypy.rpython.rtuple import AbstractTupleRepr
        if arguments.w_stararg != hop.nb_args - 3:
            raise TyperError("call pattern too complex")
        hop.nb_args -= 1
        v_tuple = hop.args_v.pop()
        s_tuple = hop.args_s.pop()
        r_tuple = hop.args_r.pop()
        if not isinstance(r_tuple, AbstractTupleRepr):
            raise TyperError("*arg must be a tuple")
        for i in range(len(r_tuple.items_r)):
            v_item = r_tuple.getitem_internal(hop.llops, v_tuple, i)
            hop.nb_args += 1
            hop.args_v.append(v_item)
            hop.args_s.append(s_tuple.items[i])
            hop.args_r.append(r_tuple.items_r[i])

    kwds = arguments.kwds_w or {}
    if not takes_kwds and kwds:
        raise TyperError("kwds args not supported")
    # prefix keyword arguments with 'i_'
    kwds_i = {}
    for key, index in kwds.items():
        kwds_i['i_'+key] = index

    return hop, kwds_i


class BuiltinFunctionRepr(Repr):
    lowleveltype = lltype.Void

    def __init__(self, builtinfunc):
        self.builtinfunc = builtinfunc

    def findbltintyper(self, rtyper):
        "Find the function to use to specialize calls to this built-in func."
        try:
            return BUILTIN_TYPER[self.builtinfunc]
        except (KeyError, TypeError):
            pass
        try:
            return rtyper.type_system.rbuiltin.BUILTIN_TYPER[self.builtinfunc]
        except (KeyError, TypeError):
            pass
        if extregistry.is_registered(self.builtinfunc):
            entry = extregistry.lookup(self.builtinfunc)
            return entry.specialize_call
        raise TyperError("don't know about built-in function %r" % (
            self.builtinfunc,))

    def rtype_simple_call(self, hop):
        bltintyper = self.findbltintyper(hop.rtyper)
        hop2 = hop.copy()
        hop2.r_s_popfirstarg()
        return bltintyper(hop2)

    def rtype_call_args(self, hop):
        # calling a built-in function with keyword arguments:
        # mostly for rpython.objectmodel.hint()
        hop, kwds_i = call_args_expand(hop)

        bltintyper = self.findbltintyper(hop.rtyper)
        hop2 = hop.copy()
        hop2.r_s_popfirstarg()
        hop2.r_s_popfirstarg()
        # the RPython-level keyword args are passed with an 'i_' prefix and
        # the corresponding value is an *index* in the hop2 arguments,
        # to be used with hop.inputarg(arg=..)
        return bltintyper(hop2, **kwds_i)


class BuiltinMethodRepr(Repr):

    def __init__(self, rtyper, s_self, methodname):
        self.s_self = s_self
        self.self_repr = rtyper.getrepr(s_self)
        self.methodname = methodname
        # methods of a known name are implemented as just their 'self'
        self.lowleveltype = self.self_repr.lowleveltype

    def convert_const(self, obj):
        return self.self_repr.convert_const(get_builtin_method_self(obj))

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
            c = get_builtin_method_self(c)
            hop2.args_v[0] = Constant(c)
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

def parse_kwds(hop, *argspec_i_r):
    lst = [i for (i, r) in argspec_i_r if i is not None]
    lst.sort()
    if lst != range(hop.nb_args - len(lst), hop.nb_args):
        raise TyperError("keyword args are expected to be at the end of "
                         "the 'hop' arg list")
    result = []
    for i, r in argspec_i_r:
        if i is not None:
            if r is None:
                r = hop.args_r[i]
            result.append(hop.inputarg(r, arg=i))
        else:
            result.append(None)
    hop.nb_args -= len(lst)
    return result

def get_builtin_method_self(x):
    try:
        return x.__self__   # on top of CPython
    except AttributeError:
        return x.im_self    # on top of PyPy

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

def rtype_builtin_unicode(hop):
    return hop.args_r[0].rtype_unicode(hop)

def rtype_builtin_list(hop):
    return hop.args_r[0].rtype_bltn_list(hop)

#def rtype_builtin_range(hop): see rrange.py

#def rtype_builtin_xrange(hop): see rrange.py

#def rtype_r_dict(hop): see rdict.py

def rtype_intmask(hop):
    hop.exception_cannot_occur()
    vlist = hop.inputargs(lltype.Signed)
    return vlist[0]

def rtype_builtin_min(hop):
    v1, v2 = hop.inputargs(hop.r_result, hop.r_result)
    return hop.gendirectcall(ll_min, v1, v2)

def ll_min(i1, i2):
    if i1 < i2:
        return i1
    return i2

def rtype_builtin_max(hop):
    v1, v2 = hop.inputargs(hop.r_result, hop.r_result)
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
import __builtin__, exceptions
BUILTIN_TYPER = {}
for name, value in globals().items():
    if name.startswith('rtype_builtin_'):
        original = getattr(__builtin__, name[14:])
        BUILTIN_TYPER[original] = value

BUILTIN_TYPER[getattr(OSError.__init__, 'im_func', OSError.__init__)] = (
    rtype_OSError__init__)

BUILTIN_TYPER[object.__init__] = rtype_object__init__
# annotation of low-level types

def rtype_malloc(hop, i_flavor=None, i_zero=None):
    assert hop.args_s[0].is_constant()
    vlist = [hop.inputarg(lltype.Void, arg=0)]
    opname = 'malloc'
    v_flavor, v_zero = parse_kwds(hop, (i_flavor, lltype.Void), (i_zero, None))

    flags = {'flavor': 'gc'}
    if v_flavor is not None:
        flags['flavor'] = v_flavor.value
    if i_zero is not None:
        flags['zero'] = v_zero.value
    vlist.append(hop.inputconst(lltype.Void, flags))
        
    if hop.nb_args == 2:
        vlist.append(hop.inputarg(lltype.Signed, arg=1))
        opname += '_varsize'

    hop.has_implicit_exception(MemoryError)   # record that we know about it
    hop.exception_is_here()
    return hop.genop(opname, vlist, resulttype = hop.r_result.lowleveltype)

def rtype_free(hop, i_flavor):
    assert i_flavor == 1
    hop.exception_cannot_occur()
    vlist = hop.inputargs(hop.args_r[0], lltype.Void)
    hop.genop('free', vlist)

def rtype_const_result(hop):
    hop.exception_cannot_occur()
    return hop.inputconst(hop.r_result.lowleveltype, hop.s_result.const)

def rtype_cast_pointer(hop):
    assert hop.args_s[0].is_constant()
    assert isinstance(hop.args_r[1], rptr.PtrRepr)
    v_type, v_input = hop.inputargs(lltype.Void, hop.args_r[1])
    hop.exception_cannot_occur()
    return hop.genop('cast_pointer', [v_input],    # v_type implicit in r_result
                     resulttype = hop.r_result.lowleveltype)

def rtype_cast_opaque_ptr(hop):
    assert hop.args_s[0].is_constant()
    assert isinstance(hop.args_r[1], rptr.PtrRepr)
    v_type, v_input = hop.inputargs(lltype.Void, hop.args_r[1])
    hop.exception_cannot_occur()
    return hop.genop('cast_opaque_ptr', [v_input], # v_type implicit in r_result
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
    v_type, v_value = hop.inputargs(lltype.Void, hop.args_r[1])
    return gen_cast(hop.llops, TGT, v_value)

_cast_to_Signed = {
    lltype.Signed:         None,
    lltype.Bool:           'cast_bool_to_int',
    lltype.Char:           'cast_char_to_int',
    lltype.UniChar:        'cast_unichar_to_int',
    lltype.Float:          'cast_float_to_int',
    lltype.Unsigned:       'cast_uint_to_int',
    lltype.SignedLongLong: 'truncate_longlong_to_int',
    }
_cast_from_Signed = {
    lltype.Signed:         None,
    lltype.Bool:           'int_is_true',
    lltype.Char:           'cast_int_to_char',
    lltype.UniChar:        'cast_int_to_unichar',
    lltype.Float:          'cast_int_to_float',
    lltype.Unsigned:       'cast_int_to_uint',
    lltype.SignedLongLong: 'cast_int_to_longlong',
    }
def gen_cast(llops, TGT, v_value):
    ORIG = v_value.concretetype
    if ORIG == TGT:
        return v_value
    if (isinstance(TGT, lltype.Primitive) and
        isinstance(ORIG, lltype.Primitive)):
        if ORIG in _cast_to_Signed and TGT in _cast_from_Signed:
            op = _cast_to_Signed[ORIG]
            if op:
                v_value = llops.genop(op, [v_value], resulttype=lltype.Signed)
            op = _cast_from_Signed[TGT]
            if op:
                v_value = llops.genop(op, [v_value], resulttype=TGT)
            return v_value
        else:
            # use the generic operation if there is no alternative
            return llops.genop('cast_primitive', [v_value], resulttype=TGT)
    elif isinstance(TGT, lltype.Ptr):
        if isinstance(ORIG, lltype.Ptr):
            if (isinstance(TGT.TO, lltype.OpaqueType) or
                isinstance(ORIG.TO, lltype.OpaqueType)):
                return llops.genop('cast_opaque_ptr', [v_value],
                                                              resulttype = TGT)
            else:
                return llops.genop('cast_pointer', [v_value], resulttype = TGT)
        elif ORIG == llmemory.Address:
            return llops.genop('cast_adr_to_ptr', [v_value], resulttype = TGT)
        elif isinstance(ORIG, lltype.Primitive):
            v_value = gen_cast(llops, lltype.Signed, v_value)            
            return llops.genop('cast_int_to_ptr', [v_value], resulttype=TGT)
    elif TGT == llmemory.Address and isinstance(ORIG, lltype.Ptr):
        return llops.genop('cast_ptr_to_adr', [v_value], resulttype = TGT)
    elif isinstance(TGT, lltype.Primitive):
        if isinstance(ORIG, lltype.Ptr):
            v_value = llops.genop('cast_ptr_to_int', [v_value],
                                  resulttype=lltype.Signed)
        elif ORIG == llmemory.Address:
            v_value = llops.genop('cast_adr_to_int', [v_value],
                                  resulttype=lltype.Signed)
        else:
            raise TypeError("don't know how to cast from %r to %r" % (ORIG,
                                                                      TGT))
        return gen_cast(llops, TGT, v_value)
    raise TypeError("don't know how to cast from %r to %r" % (ORIG, TGT))

def rtype_cast_ptr_to_int(hop):
    assert isinstance(hop.args_r[0], rptr.PtrRepr)
    vlist = hop.inputargs(hop.args_r[0])
    hop.exception_cannot_occur()
    return hop.genop('cast_ptr_to_int', vlist,
                     resulttype = lltype.Signed)

def rtype_cast_int_to_ptr(hop):
    assert hop.args_s[0].is_constant()
    v_type, v_input = hop.inputargs(lltype.Void, lltype.Signed)
    hop.exception_cannot_occur()
    return hop.genop('cast_int_to_ptr', [v_input],
                     resulttype = hop.r_result.lowleveltype)

def rtype_runtime_type_info(hop):
    assert isinstance(hop.args_r[0], rptr.PtrRepr)
    vlist = hop.inputargs(hop.args_r[0])
    return hop.genop('runtime_type_info', vlist,
                     resulttype = hop.r_result.lowleveltype)

BUILTIN_TYPER[lltype.malloc] = rtype_malloc
BUILTIN_TYPER[lltype.free] = rtype_free
BUILTIN_TYPER[lltype.cast_primitive] = rtype_cast_primitive
BUILTIN_TYPER[lltype.cast_pointer] = rtype_cast_pointer
BUILTIN_TYPER[lltype.cast_opaque_ptr] = rtype_cast_opaque_ptr
BUILTIN_TYPER[lltype.direct_fieldptr] = rtype_direct_fieldptr
BUILTIN_TYPER[lltype.direct_arrayitems] = rtype_direct_arrayitems
BUILTIN_TYPER[lltype.direct_ptradd] = rtype_direct_ptradd
BUILTIN_TYPER[lltype.cast_ptr_to_int] = rtype_cast_ptr_to_int
BUILTIN_TYPER[lltype.cast_int_to_ptr] = rtype_cast_int_to_ptr
BUILTIN_TYPER[lltype.typeOf] = rtype_const_result
BUILTIN_TYPER[lltype.nullptr] = rtype_const_result
BUILTIN_TYPER[lltype.getRuntimeTypeInfo] = rtype_const_result
BUILTIN_TYPER[lltype.Ptr] = rtype_const_result
BUILTIN_TYPER[lltype.runtime_type_info] = rtype_runtime_type_info
BUILTIN_TYPER[rarithmetic.intmask] = rtype_intmask
BUILTIN_TYPER[objectmodel.we_are_translated] = rtype_we_are_translated

BUILTIN_TYPER[objectmodel.hlinvoke] = rtype_hlinvoke


# _________________________________________________________________
# memory addresses

from pypy.rpython.lltypesystem import llmemory

def rtype_raw_malloc(hop):
    v_size, = hop.inputargs(lltype.Signed)
    return hop.genop('raw_malloc', [v_size], resulttype=llmemory.Address)

def rtype_raw_malloc_usage(hop):
    v_size, = hop.inputargs(lltype.Signed)
    hop.exception_cannot_occur()
    return hop.genop('raw_malloc_usage', [v_size], resulttype=lltype.Signed)

def rtype_raw_free(hop):
    v_addr, = hop.inputargs(llmemory.Address)
    hop.exception_cannot_occur()
    return hop.genop('raw_free', [v_addr])

def rtype_raw_memcopy(hop):
    v_list = hop.inputargs(llmemory.Address, llmemory.Address, lltype.Signed)
    hop.exception_cannot_occur()
    return hop.genop('raw_memcopy', v_list)

def rtype_raw_memclear(hop):
    v_list = hop.inputargs(llmemory.Address, lltype.Signed)
    return hop.genop('raw_memclear', v_list)

BUILTIN_TYPER[llmemory.raw_malloc] = rtype_raw_malloc
BUILTIN_TYPER[llmemory.raw_malloc_usage] = rtype_raw_malloc_usage
BUILTIN_TYPER[llmemory.raw_free] = rtype_raw_free
BUILTIN_TYPER[llmemory.raw_memclear] = rtype_raw_memclear
BUILTIN_TYPER[llmemory.raw_memcopy] = rtype_raw_memcopy

def rtype_offsetof(hop):
    TYPE, field = hop.inputargs(lltype.Void, lltype.Void)
    return hop.inputconst(lltype.Signed,
                          llmemory.offsetof(TYPE.value, field.value))

BUILTIN_TYPER[llmemory.offsetof] = rtype_offsetof

# _________________________________________________________________
# non-gc objects

def rtype_free_non_gc_object(hop):
    vinst, = hop.inputargs(hop.args_r[0])
    flavor = hop.args_r[0].gcflavor
    assert flavor != 'gc'
    cflavor = hop.inputconst(lltype.Void, flavor)
    return hop.genop('free', [vinst, cflavor])
    
BUILTIN_TYPER[objectmodel.free_non_gc_object] = rtype_free_non_gc_object

# keepalive_until_here

def rtype_keepalive_until_here(hop):
    for v in hop.args_v:
        hop.genop('keepalive', [v], resulttype=lltype.Void)
    return hop.inputconst(lltype.Void, None)

BUILTIN_TYPER[objectmodel.keepalive_until_here] = rtype_keepalive_until_here

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

def rtype_cast_int_to_adr(hop):
    v_input, = hop.inputargs(lltype.Signed)
    hop.exception_cannot_occur()
    return hop.genop('cast_int_to_adr', [v_input],
                     resulttype = llmemory.Address)


BUILTIN_TYPER[llmemory.cast_ptr_to_adr] = rtype_cast_ptr_to_adr
BUILTIN_TYPER[llmemory.cast_adr_to_ptr] = rtype_cast_adr_to_ptr
BUILTIN_TYPER[llmemory.cast_adr_to_int] = rtype_cast_adr_to_int
BUILTIN_TYPER[llmemory.cast_int_to_adr] = rtype_cast_int_to_adr

