from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib import jit, jit_libffi, rdynload, objectmodel
from rpython.tool import leakfinder

from pypy.interpreter.error import OperationError

from pypy.module._cffi_backend import ctypefunc, ctypeprim, ctypeptr, misc

from pypy.module.cppyy.capi.capi_types import C_SCOPE, C_TYPE, C_OBJECT,\
   C_METHOD, C_INDEX, C_INDEX_ARRAY, WLAVC_INDEX, C_METHPTRGETTER_PTR

import reflex_capi as backend

reflection_library = 'rflxlib.so'

def identify():
    return 'loadable_capi'

class _Arg:         # poor man's union
    _immutable_ = True
    def __init__(self, l = 0, s = '', vp = rffi.cast(rffi.VOIDP, 0) ):
        self._long = l
        self._string = s
        self._voidp = vp

# For the loadable CAPI, the calls start and end in RPython. Therefore, the standard
# _call of W_CTypeFunc, which expects wrapped objects, does not quite work: some
# vars (e.g. void* equivalent) can not be wrapped, and others (such as rfloat) risk
# rounding problems. This W_RCTypeFun then, takes args, instead of args_w. Note that
# rcall() is a new method, so as to not interfere with the base class call and _call
# when rtyping. It is also called directly (see call_capi below).
class W_RCTypeFunc(ctypefunc.W_CTypeFunc):
    @jit.unroll_safe
    def rcall(self, funcaddr, args):
        assert self.cif_descr
        self = jit.promote(self)
        # no checking of len(args) needed, as calls in this context are not dynamic

        # The following code is functionally similar to W_CTypeFunc._call, but its
        # implementation is tailored to the restricted use (include memory handling)
        # of the CAPI calls.
        space = self.space
        cif_descr = self.cif_descr
        size = cif_descr.exchange_size
        raw_string = rffi.cast(rffi.CCHARP, 0)    # only ever have one in the CAPI
        buffer = lltype.malloc(rffi.CCHARP.TO, size, flavor='raw')
        try:
            for i in range(len(args)):
                data = rffi.ptradd(buffer, cif_descr.exchange_args[i])
                obj = args[i]
                argtype = self.fargs[i]
                # the following is clumsy, but the data types used as arguments are
                # very limited, so it'll do for now
                if isinstance(argtype, ctypeprim.W_CTypePrimitiveSigned):
                    misc.write_raw_integer_data(data, rffi.cast(rffi.LONG, obj._long), argtype.size)
                elif isinstance(argtype, ctypeprim.W_CTypePrimitiveUnsigned):
                    misc.write_raw_integer_data(data, rffi.cast(rffi.ULONG, obj._long), argtype.size)
                elif obj._voidp != rffi.cast(rffi.VOIDP, 0):
                    data = rffi.cast(rffi.VOIDPP, data)
                    data[0] = obj._voidp
                else:    # only other use is sring
                    n = len(obj._string)
                    assert raw_string == rffi.cast(rffi.CCHARP, 0)
                    raw_string = lltype.malloc(rffi.CCHARP.TO, n+1, flavor='raw')
                    for j in range(n):
                        raw_string[j] = obj._string[j]
                    raw_string[n] = '\x00'
                    data = rffi.cast(rffi.CCHARPP, data)
                    data[0] = raw_string

            jit_libffi.jit_ffi_call(cif_descr,
                                    rffi.cast(rffi.VOIDP, funcaddr),
                                    buffer)

            resultdata = rffi.ptradd(buffer, cif_descr.exchange_result)
        finally:
            if raw_string != rffi.cast(rffi.CCHARP, 0):
                lltype.free(raw_string, flavor='raw')
            lltype.free(buffer, flavor='raw')
        return rffi.cast(rffi.LONGP, resultdata)

std_string_name = backend.std_string_name

ts_reflect = backend.ts_reflect
ts_call    = backend.ts_call
ts_memory  = backend.ts_memory
ts_helper  = backend.ts_helper

c_load_dictionary = backend.c_load_dictionary

class State(object):
    def __init__(self, space):
        self.library = None
        self.capi_calls = {}

        import pypy.module._cffi_backend.newtype as nt

        # TODO: the following need to match up with the globally defined C_XYZ low-level
        # types (see capi/__init__.py), but by using strings here, that isn't guaranteed
        c_opaque_ptr = nt.new_primitive_type(space, 'long')
 
        c_scope  = c_opaque_ptr
        c_type   = c_scope
        c_object = c_opaque_ptr
        c_method = c_opaque_ptr
        c_index  = nt.new_primitive_type(space, 'long')

        c_void   = nt.new_void_type(space)
        c_char   = nt.new_primitive_type(space, 'char')
        c_uchar  = nt.new_primitive_type(space, 'unsigned char')
        c_short  = nt.new_primitive_type(space, 'short')
        c_int    = nt.new_primitive_type(space, 'int')
        c_long   = nt.new_primitive_type(space, 'long')
        c_llong  = nt.new_primitive_type(space, 'long long')
        c_float  = nt.new_primitive_type(space, 'float')
        c_double = nt.new_primitive_type(space, 'double')

        c_ccharp = nt.new_pointer_type(space, c_char)
        c_index_array = nt.new_primitive_type(space, 'unsigned long')     # likewise ...

        c_voidp  = nt.new_pointer_type(space, c_void)
        c_size_t = nt.new_primitive_type(space, 'size_t')

        self.capi_call_ifaces = {
            # name to opaque C++ scope representation
            'num_scopes'   : ([c_scope],                              c_int),
            'scope_name'   : ([c_scope, c_int],                       c_ccharp),

            'resolve_name' : ([c_ccharp],                             c_ccharp),
            'get_scope'    : ([c_ccharp],                             c_scope),
            'get_template' : ([c_ccharp],                             c_type),
            'actual_class' : ([c_type, c_object],                     c_type),

            # memory management
            'allocate'     : ([c_type],                               c_object),
            'deallocate'   : ([c_type, c_object],                     c_void),
            'destruct'     : ([c_type, c_object],                     c_void),

            # method/function dispatching
            'call_v'       : ([c_method, c_object, c_int, c_voidp],   c_void),
            'call_b'       : ([c_method, c_object, c_int, c_voidp],   c_uchar),
            'call_c'       : ([c_method, c_object, c_int, c_voidp],   c_char),
            'call_h'       : ([c_method, c_object, c_int, c_voidp],   c_short),
            'call_i'       : ([c_method, c_object, c_int, c_voidp],   c_int),
            'call_l'       : ([c_method, c_object, c_int, c_voidp],   c_long),
            'call_ll'      : ([c_method, c_object, c_int, c_voidp],   c_llong),
            'call_f'       : ([c_method, c_object, c_int, c_voidp],   c_float),
            'call_d'       : ([c_method, c_object, c_int, c_voidp],   c_double),

            'call_r'       : ([c_method, c_object, c_int, c_voidp],   c_voidp),
            'call_s'       : ([c_method, c_object, c_int, c_voidp],   c_ccharp),

            'constructor'  : ([c_method, c_object, c_int, c_voidp],   c_object),
            'call_o'       : ([c_method, c_object, c_int, c_voidp, c_type],     c_object),

            'get_methptr_getter' : ([c_scope, c_index],               c_voidp), # TODO: verify

            # handling of function argument buffer
            'allocate_function_args'   : ([c_size_t],                 c_voidp),
            'deallocate_function_args' : ([c_voidp],                  c_void),
            'function_arg_sizeof'      : ([],                         c_size_t),
            'function_arg_typeoffset'  : ([],                         c_size_t),

            # scope reflection information
            'is_namespace'          : ([c_scope],                     c_int),
            'is_enum'               : ([c_ccharp],                    c_int),

            # type/class reflection information
            'final_name'            : ([c_type],                      c_ccharp),
            'scoped_final_name'     : ([c_type],                      c_ccharp),
            'has_complex_hierarchy' : ([c_type],                      c_int),
            'num_bases'             : ([c_type],                      c_int),
            'base_name'             : ([c_type, c_int],               c_ccharp),
            'is_subtype'            : ([c_type, c_type],              c_int),

            'base_offset'           : ([c_type, c_type, c_object, c_int],       c_long),

            # method/function reflection information
            'num_methods'           : ([c_scope],                     c_int),
            'method_index_at'       : ([c_scope, c_int],              c_index),
            'method_indices_from_name' : ([c_scope, c_ccharp],        c_index_array),

            'method_name'           : ([c_scope, c_index],            c_ccharp),
            'method_result_type'    : ([c_scope, c_index],            c_ccharp),
            'method_num_args'       : ([c_scope, c_index],            c_int),

            'method_arg_type'       : ([c_scope, c_index, c_int],     c_ccharp),
            'method_arg_default'    : ([c_scope, c_index, c_int],     c_ccharp),
            'method_signature'      : ([c_scope, c_index],            c_ccharp),

            'method_template_arg_name' : ([c_scope, c_index, c_index],          c_ccharp),

            # data member reflection information
            'datamember_name'       : ([c_scope, c_int],              c_ccharp),
            'datamember_type'       : ([c_scope, c_int],              c_ccharp),

            # misc helpers
            'free'         : ([c_voidp],                              c_void),
        }

def load_reflection_library(space):
    state = space.fromcache(State)
    if state.library is None:
        from pypy.module._cffi_backend.libraryobj import W_Library
        state.library = W_Library(space, reflection_library, rdynload.RTLD_LOCAL | rdynload.RTLD_LAZY)
    return state.library

def verify_backend(space):
    try:
        load_reflection_library(space)
    except Exception:
        if objectmodel.we_are_translated():
            raise OperationError(space.w_ImportError,
                                 space.wrap("missing reflection library rflxlib.so"))
        return False
    return True

def call_capi(space, name, args):
    state = space.fromcache(State)
    try:
        c_call = state.capi_calls[name]
    except KeyError:
        if state.library is None:
            load_reflection_library(space)
        iface = state.capi_call_ifaces[name]
        cfunc = W_RCTypeFunc(space, iface[0], iface[1], False)
        c_call = state.library.load_function(cfunc, 'cppyy_'+name)
        # TODO: there must be a better way to trick the leakfinder ...
        if not objectmodel.we_are_translated():
            leakfinder.remember_free(c_call.ctype.cif_descr._obj0)
        state.capi_calls[name] = c_call
    return c_call.ctype.rcall(c_call._cdata, args)

def _longptr_to_int(longptr):
    return int(rffi.cast(rffi.INTP, longptr)[0])

# name to opaque C++ scope representation ------------------------------------
def c_num_scopes(space, cppscope):
    return call_capi(space, 'num_scopes', [_Arg(l=cppscope.handle)])[0]
def c_scope_name(space, cppscope, iscope):
    args = [_Arg(l=cppscope.handle), _Arg(l=iscope)]
    return charp2str_free(space, call_capi(space, 'scope_name', args))

def c_resolve_name(space, name):
    return charp2str_free(space, call_capi(space, 'resolve_name', [_Arg(s=name)]))
def c_get_scope_opaque(space, name):
    return rffi.cast(C_SCOPE, call_capi(space, 'get_scope', [_Arg(s=name)])[0])
def c_get_template(space, name):
    return rffi.cast(C_TYPE, call_capi(space, 'get_template', [_Arg(s=name)])[0])
def c_actual_class(space, cppclass, cppobj):
    args = [_Arg(l=cppclass.handle), _Arg(l=cppobj)]
    return rffi.cast(C_TYPE, call_capi(space, 'actual_class', args)[0])

# memory management ----------------------------------------------------------
def c_allocate(space, cppclass):
    return rffi.cast(C_OBJECT, call_capi(space, 'allocate', [_Arg(l=cppclass.handle)])[0])
def c_deallocate(space, cppclass, cppobject):
    call_capi(space, 'deallocate', [_Arg(l=cppclass.handle), _Arg(l=cppobject)])
def c_destruct(space, cppclass, cppobject):
    call_capi(space, 'destruct', [_Arg(l=cppclass.handle), _Arg(l=cppobject)])

# method/function dispatching ------------------------------------------------
def c_call_v(space, cppmethod, cppobject, nargs, cargs):
    args = [_Arg(l=cppmethod), _Arg(l=cppobject), _Arg(l=nargs), _Arg(vp=cargs)]
    call_capi(space, 'call_v', args)
def c_call_b(space, cppmethod, cppobject, nargs, cargs):
    args = [_Arg(l=cppmethod), _Arg(l=cppobject), _Arg(l=nargs), _Arg(vp=cargs)]
    return rffi.cast(rffi.UCHARP, call_capi(space, 'call_b', args))[0]
def c_call_c(space, cppmethod, cppobject, nargs, cargs):
    args = [_Arg(l=cppmethod), _Arg(l=cppobject), _Arg(l=nargs), _Arg(vp=cargs)]
    return rffi.cast(rffi.CCHARP, call_capi(space, 'call_c', args))[0]
def c_call_h(space, cppmethod, cppobject, nargs, cargs):
    args = [_Arg(l=cppmethod), _Arg(l=cppobject), _Arg(l=nargs), _Arg(vp=cargs)]
    return rffi.cast(rffi.SHORTP, call_capi(space, 'call_h', args))[0]
def c_call_i(space, cppmethod, cppobject, nargs, cargs):
    args = [_Arg(l=cppmethod), _Arg(l=cppobject), _Arg(l=nargs), _Arg(vp=cargs)]
    return rffi.cast(rffi.INTP, call_capi(space, 'call_i', args))[0]
def c_call_l(space, cppmethod, cppobject, nargs, cargs):
    args = [_Arg(l=cppmethod), _Arg(l=cppobject), _Arg(l=nargs), _Arg(vp=cargs)]
    return rffi.cast(rffi.LONGP, call_capi(space, 'call_l', args))[0]
def c_call_ll(space, cppmethod, cppobject, nargs, cargs):
    args = [_Arg(l=cppmethod), _Arg(l=cppobject), _Arg(l=nargs), _Arg(vp=cargs)]
    return rffi.cast(rffi.LONGLONGP, call_capi(space, 'call_ll', args))[0]
def c_call_f(space, cppmethod, cppobject, nargs, cargs):
    args = [_Arg(l=cppmethod), _Arg(l=cppobject), _Arg(l=nargs), _Arg(vp=cargs)]
    return rffi.cast(rffi.FLOATP, call_capi(space, 'call_f', args))[0]
def c_call_d(space, cppmethod, cppobject, nargs, cargs):
    args = [_Arg(l=cppmethod), _Arg(l=cppobject), _Arg(l=nargs), _Arg(vp=cargs)]
    return rffi.cast(rffi.DOUBLEP, call_capi(space, 'call_d', args))[0]

def c_call_r(space, cppmethod, cppobject, nargs, cargs):
    args = [_Arg(l=cppmethod), _Arg(l=cppobject), _Arg(l=nargs), _Arg(vp=cargs)]
    return rffi.cast(rffi.VOIDPP, call_capi(space, 'call_r', args))[0]
def c_call_s(space, cppmethod, cppobject, nargs, cargs):
    args = [_Arg(l=cppmethod), _Arg(l=cppobject), _Arg(l=nargs), _Arg(vp=cargs)]
    return call_capi(space, 'call_s', args)

def c_constructor(space, cppmethod, cppobject, nargs, cargs):
    args = [_Arg(l=cppmethod), _Arg(l=cppobject), _Arg(l=nargs), _Arg(vp=cargs)]
    return rffi.cast(C_OBJECT, call_capi(space, 'constructor', args)[0])
def c_call_o(space, cppmethod, cppobject, nargs, cargs, cppclass):
    args = [_Arg(l=cppmethod), _Arg(l=cppobject), _Arg(l=nargs), _Arg(vp=cargs), _Arg(l=cppclass.handle)]
    return rffi.cast(C_OBJECT, call_capi(space, 'call_o', args)[0])

@jit.elidable_promote()
def c_get_methptr_getter(space, cppscope, index):
    args = [_Arg(l=cppscope.handle), _Arg(l=index)]
    return rffi.cast(C_METHPTRGETTER_PTR, call_capi(space, 'get_methptr_getter', args)[0])

# handling of function argument buffer ---------------------------------------
def c_allocate_function_args(space, size):
    return rffi.cast(rffi.VOIDP, call_capi(space, 'allocate_function_args', [_Arg(l=size)])[0])
def c_deallocate_function_args(space, cargs):
    call_capi(space, 'deallocate_function_args', [_Arg(vp=cargs)])
@jit.elidable_promote()
def c_function_arg_sizeof(space):
    return rffi.cast(rffi.SIZE_T, call_capi(space, 'function_arg_sizeof', [])[0])
@jit.elidable_promote()
def c_function_arg_typeoffset(space):
    return rffi.cast(rffi.SIZE_T, call_capi(space, 'function_arg_typeoffset', [])[0])

# scope reflection information -----------------------------------------------
def c_is_namespace(space, scope):
    return _longptr_to_int(call_capi(space, 'is_namespace', [_Arg(l=scope)]))
def c_is_enum(space, name):
    return _longptr_to_int(call_capi(space, 'is_enum', [_Arg(s=name)]))

# type/class reflection information ------------------------------------------
def c_final_name(space, cpptype):
    return charp2str_free(space, call_capi(space, 'final_name', [_Arg(l=cpptype)]))
def c_scoped_final_name(space, cpptype):
    return charp2str_free(space, call_capi(space, 'scoped_final_name', [_Arg(l=cpptype)]))
def c_has_complex_hierarchy(space, handle):
    return _longptr_to_int(call_capi(space, 'has_complex_hierarchy', [_Arg(l=handle)]))
def c_num_bases(space, cppclass):
    return _longptr_to_int(call_capi(space, 'num_bases', [_Arg(l=cppclass.handle)]))
def c_base_name(space, cppclass, base_index):
    args = [_Arg(l=cppclass.handle), _Arg(l=base_index)]
    return charp2str_free(space, call_capi(space, 'base_name', args))
@jit.elidable_promote()
def c_is_subtype(space, derived, base):
    if derived == base:
        return 1
    return _longptr_to_int(call_capi(space, 'is_subtype', [_Arg(l=derived.handle), _Arg(l=base.handle)]))

@jit.elidable_promote()
def _c_base_offset(space, derived_h, base_h, address, direction):
    args = [_Arg(l=derived_h), _Arg(l=base_h), _Arg(l=address), _Arg(l=direction)]
    return rffi.cast(rffi.SIZE_T, rffi.cast(rffi.ULONGP, call_capi(space, 'base_offset', args))[0])
@jit.elidable_promote()
def c_base_offset(space, derived, base, address, direction):
    if derived == base:
        return 0
    return _c_base_offset(space, derived.handle, base.handle, address, direction)
@jit.elidable_promote()
def c_base_offset1(space, derived_h, base, address, direction):
    return _c_base_offset(space, derived_h, base.handle, address, direction)

# method/function reflection information -------------------------------------
def c_num_methods(space, cppscope):
    args = [_Arg(l=cppscope.handle)]
    return _longptr_to_int(call_capi(space, 'num_methods', args))
def c_method_index_at(space, cppscope, imethod):
    args = [_Arg(l=cppscope.handle), _Arg(l=imethod)]
    return call_capi(space, 'method_index_at', args)[0]
def c_method_indices_from_name(space, cppscope, name):
    args = [_Arg(l=cppscope.handle), _Arg(s=name)]
    indices = rffi.cast(C_INDEX_ARRAY, call_capi(space, 'method_indices_from_name', args)[0])
    if not indices:
        return []
    py_indices = []
    i = 0
    index = indices[i]
    while index != -1:
        i += 1
        py_indices.append(index)
        index = indices[i]
    c_free(space, rffi.cast(rffi.VOIDP, indices))   # c_free defined below
    return py_indices

def c_method_name(space, cppscope, index):
    args = [_Arg(l=cppscope.handle), _Arg(l=index)]
    return charp2str_free(space, call_capi(space, 'method_name', args))
def c_method_result_type(space, cppscope, index):
    args = [_Arg(l=cppscope.handle), _Arg(l=index)]
    return charp2str_free(space, call_capi(space, 'method_result_type', args))
_c_method_num_args = rffi.llexternal(
    "cppyy_method_num_args",
    [C_SCOPE, C_INDEX], rffi.INT,
    threadsafe=ts_reflect,
    compilation_info=backend.eci)
def c_method_num_args(cppscope, index):
    args = [_Arg(l=cppscope.handle), _Arg(l=index)]
    return _c_method_num_args(cppscope.handle, index)
_c_method_req_args = rffi.llexternal(
    "cppyy_method_req_args",
    [C_SCOPE, C_INDEX], rffi.INT,
    threadsafe=ts_reflect,
    compilation_info=backend.eci)
def c_method_req_args(cppscope, index):
    return _c_method_req_args(cppscope.handle, index)
def c_method_arg_type(space, cppscope, index, arg_index):
    args = [_Arg(l=cppscope.handle), _Arg(l=index), _Arg(l=arg_index)]
    return charp2str_free(space, call_capi(space, 'method_arg_type', args))
def c_method_arg_default(space, cppscope, index, arg_index):
    args = [_Arg(l=cppscope.handle), _Arg(l=index), _Arg(l=arg_index)]
    return charp2str_free(space, call_capi(space, 'method_arg_default', args))
def c_method_signature(space, cppscope, index):
    args = [_Arg(l=cppscope.handle), _Arg(l=index)]
    return charp2str_free(space, call_capi(space, 'method_signature', args))

_c_method_is_template = rffi.llexternal(
    "cppyy_method_is_template",
    [C_SCOPE, C_INDEX], rffi.INT,
    threadsafe=ts_reflect,
    compilation_info=backend.eci)
def c_method_is_template(cppscope, index):
    return _c_method_is_template(cppscope.handle, index)
_c_method_num_template_args = rffi.llexternal(
    "cppyy_method_num_template_args",
    [C_SCOPE, C_INDEX], rffi.INT,
    threadsafe=ts_reflect,
    compilation_info=backend.eci)
def c_template_args(space, cppscope, index):
    nargs = _c_method_num_template_args(cppscope.handle, index)
    arg1 = _Arg(l=cppscope.handle)
    arg2 = _Arg(l=index)
    args = [c_resolve_name(space, charp2str_free(space,
                call_capi(space, 'method_template_arg_name', [arg1, arg2, _Arg(l=iarg)]))
            ) for iarg in range(nargs)]
    return args

_c_get_method = rffi.llexternal(
    "cppyy_get_method",
    [C_SCOPE, C_INDEX], C_METHOD,
    threadsafe=ts_reflect,
    compilation_info=backend.eci)
def c_get_method(cppscope, index):
    return _c_get_method(cppscope.handle, index)
_c_get_global_operator = rffi.llexternal(
    "cppyy_get_global_operator",
    [C_SCOPE, C_SCOPE, C_SCOPE, rffi.CCHARP], WLAVC_INDEX,
    threadsafe=ts_reflect,
    compilation_info=backend.eci)
def c_get_global_operator(nss, lc, rc, op):
    if nss is not None:
        return _c_get_global_operator(nss.handle, lc.handle, rc.handle, op)
    return rffi.cast(WLAVC_INDEX, -1)

# method properties ----------------------------------------------------------
_c_is_constructor = rffi.llexternal(
    "cppyy_is_constructor",
    [C_TYPE, C_INDEX], rffi.INT,
    threadsafe=ts_reflect,
    compilation_info=backend.eci)
def c_is_constructor(cppclass, index):
    return _c_is_constructor(cppclass.handle, index)
_c_is_staticmethod = rffi.llexternal(
    "cppyy_is_staticmethod",
    [C_TYPE, C_INDEX], rffi.INT,
    threadsafe=ts_reflect,
    compilation_info=backend.eci)
def c_is_staticmethod(cppclass, index):
    return _c_is_staticmethod(cppclass.handle, index)

# data member reflection information -----------------------------------------
_c_num_datamembers = rffi.llexternal(
    "cppyy_num_datamembers",
    [C_SCOPE], rffi.INT,
    threadsafe=ts_reflect,
    compilation_info=backend.eci)
def c_num_datamembers(cppscope):
    return _c_num_datamembers(cppscope.handle)
_c_datamember_name = rffi.llexternal(
    "cppyy_datamember_name",
    [C_SCOPE, rffi.INT], rffi.CCHARP,
    threadsafe=ts_reflect,
    compilation_info=backend.eci)
def c_datamember_name(space, cppscope, datamember_index):
    args = [_Arg(l=cppscope.handle), _Arg(l=datamember_index)]
    return charp2str_free(space, call_capi(space, 'datamember_name', args))
_c_datamember_type = rffi.llexternal(
    "cppyy_datamember_type",
    [C_SCOPE, rffi.INT], rffi.CCHARP,
    threadsafe=ts_reflect,
    compilation_info=backend.eci)
def c_datamember_type(space, cppscope, datamember_index):
    args = [_Arg(l=cppscope.handle), _Arg(l=datamember_index)]
    return charp2str_free(space, call_capi(space, 'datamember_type', args))
_c_datamember_offset = rffi.llexternal(
    "cppyy_datamember_offset",
    [C_SCOPE, rffi.INT], rffi.SIZE_T,
    threadsafe=ts_reflect,
    compilation_info=backend.eci)
def c_datamember_offset(cppscope, datamember_index):
    return _c_datamember_offset(cppscope.handle, datamember_index)

_c_datamember_index = rffi.llexternal(
    "cppyy_datamember_index",
    [C_SCOPE, rffi.CCHARP], rffi.INT,
    threadsafe=ts_reflect,
    compilation_info=backend.eci)
def c_datamember_index(cppscope, name):
    return _c_datamember_index(cppscope.handle, name)

# data member properties -----------------------------------------------------
_c_is_publicdata = rffi.llexternal(
    "cppyy_is_publicdata",
    [C_SCOPE, rffi.INT], rffi.INT,
    threadsafe=ts_reflect,
    compilation_info=backend.eci)
def c_is_publicdata(cppscope, datamember_index):
    return _c_is_publicdata(cppscope.handle, datamember_index)
_c_is_staticdata = rffi.llexternal(
    "cppyy_is_staticdata",
    [C_SCOPE, rffi.INT], rffi.INT,
    threadsafe=ts_reflect,
    compilation_info=backend.eci)
def c_is_staticdata(cppscope, datamember_index):
    return _c_is_staticdata(cppscope.handle, datamember_index)

# misc helpers ---------------------------------------------------------------
c_strtoll = rffi.llexternal(
    "cppyy_strtoll",
    [rffi.CCHARP], rffi.LONGLONG,
    threadsafe=ts_helper,
    compilation_info=backend.eci)
c_strtoull = rffi.llexternal(
    "cppyy_strtoull",
    [rffi.CCHARP], rffi.ULONGLONG,
    threadsafe=ts_helper,
    compilation_info=backend.eci)
def c_free(space, voidp):
    call_capi(space, 'free', [_Arg(vp=voidp)])

def charp2str_free(space, cdata):
    charp = rffi.cast(rffi.CCHARPP, cdata)[0]
    pystr = rffi.charp2str(charp)
    c_free(space, rffi.cast(rffi.VOIDP, charp))
    return pystr

c_charp2stdstring = rffi.llexternal(
    "cppyy_charp2stdstring",
    [rffi.CCHARP], C_OBJECT,
    threadsafe=ts_helper,
    compilation_info=backend.eci)
c_stdstring2stdstring = rffi.llexternal(
    "cppyy_stdstring2stdstring",
    [C_OBJECT], C_OBJECT,
    threadsafe=ts_helper,
    compilation_info=backend.eci)
c_assign2stdstring = rffi.llexternal(
    "cppyy_assign2stdstring",
    [C_OBJECT, rffi.CCHARP], lltype.Void,
    threadsafe=ts_helper,
    compilation_info=backend.eci)
c_free_stdstring = rffi.llexternal(
    "cppyy_free_stdstring",
    [C_OBJECT], lltype.Void,
    threadsafe=ts_helper,
    compilation_info=backend.eci)


# loadable-capi-specific pythonizations (none, as the capi isn't known until runtime)
def register_pythonizations(space):
    "NOT_RPYTHON"
    pass

def pythonize(space, name, w_pycppclass):
    pass
