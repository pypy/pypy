import atexit

from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib import jit, rdynload, objectmodel
from rpython.tool import leakfinder

from pypy.interpreter.error import OperationError

from pypy.module.cppyy.capi.capi_types import C_SCOPE, C_TYPE, C_OBJECT,\
   C_METHOD, C_INDEX, C_INDEX_ARRAY, WLAVC_INDEX,\
   C_METHPTRGETTER, C_METHPTRGETTER_PTR

import reflex_capi as backend

reflection_library = 'rflxlib.so'

def identify():
    return 'loadable_capi'

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
        c_voidp  = nt.new_primitive_type(space, 'unsigned long') # b/c voidp can not be wrapped

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

            # type/class reflection information
            'final_name'            : ([c_type],                      c_ccharp),
            'scoped_final_name'     : ([c_type],                      c_ccharp),
            'has_complex_hierarchy' : ([c_type],                      c_int),
            'num_bases'             : ([c_type],                      c_int),
            'base_name'             : ([c_type, c_int],               c_ccharp),

            # method/function reflection information

            'method_name'           : ([c_scope, c_index],            c_ccharp),
            'method_result_type'    : ([c_scope, c_index],            c_ccharp),

            'method_arg_type'       : ([c_scope, c_index, c_int],     c_ccharp),
            'method_arg_default'    : ([c_scope, c_index, c_int],     c_ccharp),
            'method_signature'      : ([c_scope, c_index],            c_ccharp),

            'method_template_arg_name' : ([c_scope, c_index, c_index], c_ccharp),

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

def call_capi(space, name, args_w):
    state = space.fromcache(State)
    try:
        c_call = state.capi_calls[name]
    except KeyError:
        if state.library is None:
            load_reflection_library(space)
        iface = state.capi_call_ifaces[name]
        from pypy.module._cffi_backend.ctypefunc import W_CTypeFunc
        cfunc = W_CTypeFunc(space, iface[0], iface[1], False)
        c_call = state.library.load_function(cfunc, 'cppyy_'+name)
        # TODO: there must be a better way to trick the leakfinder ...
        if not objectmodel.we_are_translated():
            leakfinder.remember_free(c_call.ctype.cif_descr._obj0)
        state.capi_calls[name] = c_call
    return c_call.call(args_w)


# name to opaque C++ scope representation ------------------------------------
def c_num_scopes(space, cppscope):
    args_w = [space.wrap(cppscope.handle)]
    return space.int_w(call_capi(space, 'num_scopes', args_w))
def c_scope_name(space, cppscope, iscope):
    args_w = [space.wrap(cppscope.handle), space.wrap(iscope)]
    return charp2str_free(space, call_capi(space, 'scope_name', args_w))

def c_resolve_name(space, name):
    args_w = [space.wrap(name)]
    return charp2str_free(space, call_capi(space, 'resolve_name', args_w))
def c_get_scope_opaque(space, name):
    args_w = [space.wrap(name)]
    return rffi.cast(C_SCOPE, space.int_w(call_capi(space, 'get_scope', args_w)))
def c_get_template(space, name):
    args_w = [space.wrap(name)]
    return rffi.cast(C_TYPE, space.int_w(call_capi(space, 'get_template', args_w)))
def c_actual_class(space, cppclass, cppobj):
    args_w = [space.wrap(cppclass.handle), space.wrap(cppobj)]
    return rffi.cast(C_TYPE, space.int_w(call_capi(space, 'actual_class', args_w)))

# memory management ----------------------------------------------------------
def c_allocate(space, cppclass):
    args_w = [space.wrap(cppclass.handle)]
    return rffi.cast(C_OBJECT, space.int_w(call_capi(space, 'allocate', args_w)))
def c_deallocate(space, cppclass, cppobject):
    args_w = [space.wrap(cppclass.handle), space.wrap(cppobject)]
    call_capi(space, 'deallocate', args_w)
def c_destruct(space, cppclass, cppobject):
    args_w = [space.wrap(cppclass.handle), space.wrap(cppobject)]
    call_capi(space, 'destruct', args_w)

# method/function dispatching ------------------------------------------------
def c_call_v(space, cppmethod, cppobject, nargs, args):
    args_w = [space.wrap(cppmethod), space.wrap(cppobject),
              space.wrap(nargs), space.wrap(rffi.cast(rffi.ULONG, args))]
    call_capi(space, 'call_v', args_w)
# TODO: these method do not actually need unwrapping, as the excutors simply
# wrap the values again, but the other backends expect that ...
def c_call_b(space, cppmethod, cppobject, nargs, args):
    args_w = [space.wrap(cppmethod), space.wrap(cppobject),
              space.wrap(nargs), space.wrap(rffi.cast(rffi.ULONG, args))]
    return rffi.cast(rffi.UCHAR, space.int_w(call_capi(space, 'call_b', args_w)))
def c_call_c(space, cppmethod, cppobject, nargs, args):
    args_w = [space.wrap(cppmethod), space.wrap(cppobject),
              space.wrap(nargs), space.wrap(rffi.cast(rffi.ULONG, args))]
    return rffi.cast(rffi.CHAR, space.str_w(call_capi(space, 'call_c', args_w)))
def c_call_h(space, cppmethod, cppobject, nargs, args):
    args_w = [space.wrap(cppmethod), space.wrap(cppobject),
              space.wrap(nargs), space.wrap(rffi.cast(rffi.ULONG, args))]
    return rffi.cast(rffi.SHORT, space.int_w(call_capi(space, 'call_h', args_w)))
def c_call_i(space, cppmethod, cppobject, nargs, args):
    args_w = [space.wrap(cppmethod), space.wrap(cppobject),
              space.wrap(nargs), space.wrap(rffi.cast(rffi.ULONG, args))]
    return rffi.cast(rffi.INT, space.int_w(call_capi(space, 'call_i', args_w)))
def c_call_l(space, cppmethod, cppobject, nargs, args):
    args_w = [space.wrap(cppmethod), space.wrap(cppobject),
              space.wrap(nargs), space.wrap(rffi.cast(rffi.ULONG, args))]
    return rffi.cast(rffi.LONG, space.int_w(call_capi(space, 'call_l', args_w)))
def c_call_ll(space, cppmethod, cppobject, nargs, args):
    args_w = [space.wrap(cppmethod), space.wrap(cppobject),
              space.wrap(nargs), space.wrap(rffi.cast(rffi.ULONG, args))]
    return rffi.cast(rffi.LONGLONG, space.int_w(call_capi(space, 'call_ll', args_w)))
def c_call_f(space, cppmethod, cppobject, nargs, args):
    args_w = [space.wrap(cppmethod), space.wrap(cppobject),
              space.wrap(nargs), space.wrap(rffi.cast(rffi.ULONG, args))]
    return rffi.cast(rffi.FLOAT, space.float_w(call_capi(space, 'call_f', args_w)))
def c_call_d(space, cppmethod, cppobject, nargs, args):
    args_w = [space.wrap(cppmethod), space.wrap(cppobject),
              space.wrap(nargs), space.wrap(rffi.cast(rffi.ULONG, args))]
    return rffi.cast(rffi.DOUBLE, space.float_w(call_capi(space, 'call_d', args_w)))

def c_call_r(space, cppmethod, cppobject, nargs, args):
    args_w = [space.wrap(cppmethod), space.wrap(cppobject),
              space.wrap(nargs), space.wrap(rffi.cast(rffi.ULONG, args))]
    return rffi.cast(rffi.VOIDP, space.int_w(call_capi(space, 'call_r', args_w)))
def c_call_s(space, cppmethod, cppobject, nargs, args):
    args_w = [space.wrap(cppmethod), space.wrap(cppobject),
              space.wrap(nargs), space.wrap(rffi.cast(rffi.ULONG, args))]
    return call_capi(space, 'call_s', args_w)

def c_constructor(space, cppmethod, cppobject, nargs, args):
    args_w = [space.wrap(cppmethod), space.wrap(cppobject),
              space.wrap(nargs), space.wrap(rffi.cast(rffi.ULONG, args))]
    return rffi.cast(C_OBJECT, space.int_w(call_capi(space, 'constructor', args_w)))
def c_call_o(space, cppmethod, cppobject, nargs, args, cppclass):
    args_w = [space.wrap(cppmethod), space.wrap(cppobject),
              space.wrap(nargs), space.wrap(rffi.cast(rffi.ULONG, args)),
              space.wrap(cppclass.handle)]
    return rffi.cast(C_OBJECT, space.int_w(call_capi(space, 'call_o', args_w)))

_c_get_methptr_getter = rffi.llexternal(
    "cppyy_get_methptr_getter",
    [C_SCOPE, C_INDEX], C_METHPTRGETTER_PTR,
    threadsafe=ts_reflect,
    compilation_info=backend.eci,
    elidable_function=True)
def c_get_methptr_getter(cppscope, index):
    return _c_get_methptr_getter(cppscope.handle, index)

# handling of function argument buffer ---------------------------------------
c_allocate_function_args = rffi.llexternal(
    "cppyy_allocate_function_args",
    [rffi.SIZE_T], rffi.VOIDP,
    threadsafe=ts_memory,
    compilation_info=backend.eci)
c_deallocate_function_args = rffi.llexternal(
    "cppyy_deallocate_function_args",
    [rffi.VOIDP], lltype.Void,
    threadsafe=ts_memory,
    compilation_info=backend.eci)
c_function_arg_sizeof = rffi.llexternal(
    "cppyy_function_arg_sizeof",
    [], rffi.SIZE_T,
    threadsafe=ts_memory,
    compilation_info=backend.eci,
    elidable_function=True)
c_function_arg_typeoffset = rffi.llexternal(
    "cppyy_function_arg_typeoffset",
    [], rffi.SIZE_T,
    threadsafe=ts_memory,
    compilation_info=backend.eci,
    elidable_function=True)

# scope reflection information -----------------------------------------------
c_is_namespace = rffi.llexternal(
    "cppyy_is_namespace",
    [C_SCOPE], rffi.INT,
    threadsafe=ts_reflect,
    compilation_info=backend.eci)
c_is_enum = rffi.llexternal(
    "cppyy_is_enum",
    [rffi.CCHARP], rffi.INT,
    threadsafe=ts_reflect,
    compilation_info=backend.eci)

# type/class reflection information ------------------------------------------
def c_final_name(space, cpptype):
    args_w = [space.wrap(cpptype)]
    return charp2str_free(space, call_capi(space, 'final_name', args_w))
def c_scoped_final_name(space, cpptype):
    args_w = [space.wrap(cpptype)]
    return charp2str_free(space, call_capi(space, 'scoped_final_name', args_w))
def c_has_complex_hierarchy(space, handle):
    args_w = [space.wrap(handle)]
    return space.int_w(call_capi(space, 'has_complex_hierarchy', args_w))
def c_num_bases(space, cppclass):
    args_w = [space.wrap(cppclass.handle)]
    return space.int_w(call_capi(space, 'num_bases', args_w))
def c_base_name(space, cppclass, base_index):
    args_w = [space.wrap(cppclass.handle), space.wrap(base_index)]
    return charp2str_free(space, call_capi(space, 'base_name', args_w))
_c_is_subtype = rffi.llexternal(
    "cppyy_is_subtype",
    [C_TYPE, C_TYPE], rffi.INT,
    threadsafe=ts_reflect,
    compilation_info=backend.eci,
    elidable_function=True)
@jit.elidable_promote()
def c_is_subtype(derived, base):
    if derived == base:
        return 1
    return _c_is_subtype(derived.handle, base.handle)

_c_base_offset = rffi.llexternal(
    "cppyy_base_offset",
    [C_TYPE, C_TYPE, C_OBJECT, rffi.INT], rffi.SIZE_T,
    threadsafe=ts_reflect,
    compilation_info=backend.eci,
    elidable_function=True)
@jit.elidable_promote()
def c_base_offset(derived, base, address, direction):
    if derived == base:
        return 0
    return _c_base_offset(derived.handle, base.handle, address, direction)
def c_base_offset1(derived_h, base, address, direction):
    return _c_base_offset(derived_h, base.handle, address, direction)

# method/function reflection information -------------------------------------
_c_num_methods = rffi.llexternal(
    "cppyy_num_methods",
    [C_SCOPE], rffi.INT,
    threadsafe=ts_reflect,
    compilation_info=backend.eci)
def c_num_methods(cppscope):
    return _c_num_methods(cppscope.handle)
_c_method_index_at = rffi.llexternal(
    "cppyy_method_index_at",
    [C_SCOPE, rffi.INT], C_INDEX,
    threadsafe=ts_reflect,
    compilation_info=backend.eci)
def c_method_index_at(cppscope, imethod):
    return _c_method_index_at(cppscope.handle, imethod)
_c_method_indices_from_name = rffi.llexternal(
    "cppyy_method_indices_from_name",
    [C_SCOPE, rffi.CCHARP], C_INDEX_ARRAY,
    threadsafe=ts_reflect,
    compilation_info=backend.eci)
def c_method_indices_from_name(space, cppscope, name):
    indices = _c_method_indices_from_name(cppscope.handle, name)
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
    args_w = [space.wrap(cppscope.handle), space.wrap(index)]
    return charp2str_free(space, call_capi(space, 'method_name', args_w))
def c_method_result_type(space, cppscope, index):
    args_w = [space.wrap(cppscope.handle), space.wrap(index)]
    return charp2str_free(space, call_capi(space, 'method_result_type', args_w))
_c_method_num_args = rffi.llexternal(
    "cppyy_method_num_args",
    [C_SCOPE, C_INDEX], rffi.INT,
    threadsafe=ts_reflect,
    compilation_info=backend.eci)
def c_method_num_args(cppscope, index):
    return _c_method_num_args(cppscope.handle, index)
_c_method_req_args = rffi.llexternal(
    "cppyy_method_req_args",
    [C_SCOPE, C_INDEX], rffi.INT,
    threadsafe=ts_reflect,
    compilation_info=backend.eci)
def c_method_req_args(cppscope, index):
    return _c_method_req_args(cppscope.handle, index)
def c_method_arg_type(space, cppscope, index, arg_index):
    args_w = [space.wrap(cppscope.handle), space.wrap(index), space.wrap(arg_index)]
    return charp2str_free(space, call_capi(space, 'method_arg_type', args_w))
def c_method_arg_default(space, cppscope, index, arg_index):
    args_w = [space.wrap(cppscope.handle), space.wrap(index), space.wrap(arg_index)]
    return charp2str_free(space, call_capi(space, 'method_arg_default', args_w))
def c_method_signature(space, cppscope, index):
    args_w = [space.wrap(cppscope.handle), space.wrap(index)]
    return charp2str_free(space, call_capi(space, 'method_signature', args_w))

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
_c_method_template_arg_name = rffi.llexternal(
    "cppyy_method_template_arg_name",
    [C_SCOPE, C_INDEX, C_INDEX], rffi.CCHARP,
    threadsafe=ts_reflect,
    compilation_info=backend.eci)
def c_template_args(space, cppscope, index):
    nargs = _c_method_num_template_args(cppscope.handle, index)
    args = [c_resolve_name(space, charp2str_free(space,
                call_capi(space, 'method_template_arg_name',
                          [space.wrap(cppscope.handle), space.wrap(index), space.wrap(iarg)])
                                     )
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
    args_w = [space.wrap(cppscope.handle), space.wrap(datamember_index)]
    return charp2str_free(space, call_capi(space, 'datamember_name', args_w))
_c_datamember_type = rffi.llexternal(
    "cppyy_datamember_type",
    [C_SCOPE, rffi.INT], rffi.CCHARP,
    threadsafe=ts_reflect,
    compilation_info=backend.eci)
def c_datamember_type(space, cppscope, datamember_index):
    args_w = [space.wrap(cppscope.handle), space.wrap(datamember_index)]
    return charp2str_free(space, call_capi(space, 'datamember_type', args_w))
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
    args_w = [space.wrap(rffi.cast(rffi.ULONG, voidp))]
    call_capi(space, 'free', args_w)

def charp2str_free(space, cdata):
    charp = rffi.cast(rffi.CCHARP, cdata._cdata)
    pystr = rffi.charp2str(charp)
    voidp = rffi.cast(rffi.VOIDP, charp)
    c_free(space, voidp)
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
