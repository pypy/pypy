from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib import jit

import reflex_capi as backend
#import cint_capi as backend

from pypy.module.cppyy.capi.capi_types import C_SCOPE, C_TYPE, C_OBJECT,\
   C_METHOD, C_INDEX, C_INDEX_ARRAY, WLAVC_INDEX,\
   C_METHPTRGETTER, C_METHPTRGETTER_PTR

identify  = backend.identify
pythonize = backend.pythonize
register_pythonizations = backend.register_pythonizations
std_string_name = backend.std_string_name

ts_reflect = backend.ts_reflect
ts_call    = backend.ts_call
ts_memory  = backend.ts_memory
ts_helper  = backend.ts_helper

def verify_backend(space):
    return True                    # by definition

c_load_dictionary = backend.c_load_dictionary

# name to opaque C++ scope representation ------------------------------------
_c_num_scopes = rffi.llexternal(
    "cppyy_num_scopes",
    [C_SCOPE], rffi.INT,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_num_scopes(space, cppscope):
    return _c_num_scopes(cppscope.handle)
_c_scope_name = rffi.llexternal(
    "cppyy_scope_name",
    [C_SCOPE, rffi.INT], rffi.CCHARP,
    compilation_info = backend.eci)
def c_scope_name(space, cppscope, iscope):
    return charp2str_free(space, _c_scope_name(cppscope.handle, iscope))

_c_resolve_name = rffi.llexternal(
    "cppyy_resolve_name",
    [rffi.CCHARP], rffi.CCHARP,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_resolve_name(space, name):
    return charp2str_free(space, _c_resolve_name(name))
_c_get_scope_opaque = rffi.llexternal(
    "cppyy_get_scope",
    [rffi.CCHARP], C_SCOPE,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_get_scope_opaque(space, name):
    return _c_get_scope_opaque(name)
_c_get_template = rffi.llexternal(
    "cppyy_get_template",
    [rffi.CCHARP], C_TYPE,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_get_template(space, name):
    return _c_get_template(name)
_c_actual_class = rffi.llexternal(
    "cppyy_actual_class",
    [C_TYPE, C_OBJECT], C_TYPE,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_actual_class(space, cppclass, cppobj):
    return _c_actual_class(cppclass.handle, cppobj)

# memory management ----------------------------------------------------------
_c_allocate = rffi.llexternal(
    "cppyy_allocate",
    [C_TYPE], C_OBJECT,
    releasegil=ts_memory,
    compilation_info=backend.eci)
def c_allocate(space, cppclass):
    return _c_allocate(cppclass.handle)
_c_deallocate = rffi.llexternal(
    "cppyy_deallocate",
    [C_TYPE, C_OBJECT], lltype.Void,
    releasegil=ts_memory,
    compilation_info=backend.eci)
def c_deallocate(space, cppclass, cppobject):
    _c_deallocate(cppclass.handle, cppobject)
_c_destruct = rffi.llexternal(
    "cppyy_destruct",
    [C_TYPE, C_OBJECT], lltype.Void,
    releasegil=ts_call,
    compilation_info=backend.eci)
def c_destruct(space, cppclass, cppobject):
    _c_destruct(cppclass.handle, cppobject)

# method/function dispatching ------------------------------------------------
_c_call_v = rffi.llexternal(
    "cppyy_call_v",
    [C_METHOD, C_OBJECT, rffi.INT, rffi.VOIDP], lltype.Void,
    releasegil=ts_call,
    compilation_info=backend.eci)
def c_call_v(space, cppmethod, cppobject, nargs, args):
    _c_call_v(cppmethod, cppobject, nargs, args)
_c_call_b = rffi.llexternal(
    "cppyy_call_b",
    [C_METHOD, C_OBJECT, rffi.INT, rffi.VOIDP], rffi.UCHAR,
    releasegil=ts_call,
    compilation_info=backend.eci)
def c_call_b(space, cppmethod, cppobject, nargs, args):
    return _c_call_b(cppmethod, cppobject, nargs, args)
_c_call_c = rffi.llexternal(
    "cppyy_call_c",
    [C_METHOD, C_OBJECT, rffi.INT, rffi.VOIDP], rffi.CHAR,
    releasegil=ts_call,
    compilation_info=backend.eci)
def c_call_c(space, cppmethod, cppobject, nargs, args):
    return _c_call_c(cppmethod, cppobject, nargs, args)
_c_call_h = rffi.llexternal(
    "cppyy_call_h",
    [C_METHOD, C_OBJECT, rffi.INT, rffi.VOIDP], rffi.SHORT,
    releasegil=ts_call,
    compilation_info=backend.eci)
def c_call_h(space, cppmethod, cppobject, nargs, args):
    return _c_call_h(cppmethod, cppobject, nargs, args)
_c_call_i = rffi.llexternal(
    "cppyy_call_i",
    [C_METHOD, C_OBJECT, rffi.INT, rffi.VOIDP], rffi.INT,
    releasegil=ts_call,
    compilation_info=backend.eci)
def c_call_i(space, cppmethod, cppobject, nargs, args):
    return _c_call_i(cppmethod, cppobject, nargs, args)
_c_call_l = rffi.llexternal(
    "cppyy_call_l",
    [C_METHOD, C_OBJECT, rffi.INT, rffi.VOIDP], rffi.LONG,
    releasegil=ts_call,
    compilation_info=backend.eci)
def c_call_l(space, cppmethod, cppobject, nargs, args):
    return _c_call_l(cppmethod, cppobject, nargs, args)
_c_call_ll = rffi.llexternal(
    "cppyy_call_ll",
    [C_METHOD, C_OBJECT, rffi.INT, rffi.VOIDP], rffi.LONGLONG,
    releasegil=ts_call,
    compilation_info=backend.eci)
def c_call_ll(space, cppmethod, cppobject, nargs, args):
    return _c_call_ll(cppmethod, cppobject, nargs, args)
_c_call_f = rffi.llexternal(
    "cppyy_call_f",
    [C_METHOD, C_OBJECT, rffi.INT, rffi.VOIDP], rffi.FLOAT,
    releasegil=ts_call,
    compilation_info=backend.eci)
def c_call_f(space, cppmethod, cppobject, nargs, args):
    return _c_call_f(cppmethod, cppobject, nargs, args)
_c_call_d = rffi.llexternal(
    "cppyy_call_d",
    [C_METHOD, C_OBJECT, rffi.INT, rffi.VOIDP], rffi.DOUBLE,
    releasegil=ts_call,
    compilation_info=backend.eci)
def c_call_d(space, cppmethod, cppobject, nargs, args):
    return _c_call_d(cppmethod, cppobject, nargs, args)

_c_call_r = rffi.llexternal(
    "cppyy_call_r",
    [C_METHOD, C_OBJECT, rffi.INT, rffi.VOIDP], rffi.VOIDP,
    releasegil=ts_call,
    compilation_info=backend.eci)
def c_call_r(space, cppmethod, cppobject, nargs, args):
    return _c_call_r(cppmethod, cppobject, nargs, args)
_c_call_s = rffi.llexternal(
    "cppyy_call_s",
    [C_METHOD, C_OBJECT, rffi.INT, rffi.VOIDP], rffi.CCHARP,
    releasegil=ts_call,
    compilation_info=backend.eci)
def c_call_s(space, cppmethod, cppobject, nargs, args):
    return _c_call_s(cppmethod, cppobject, nargs, args)

_c_constructor = rffi.llexternal(
    "cppyy_constructor",
    [C_METHOD, C_TYPE, rffi.INT, rffi.VOIDP], C_OBJECT,
    releasegil=ts_call,
    compilation_info=backend.eci)
def c_constructor(space, cppmethod, cppobject, nargs, args):
    return _c_constructor(cppmethod, cppobject, nargs, args)
_c_call_o = rffi.llexternal(
    "cppyy_call_o",
    [C_METHOD, C_OBJECT, rffi.INT, rffi.VOIDP, C_TYPE], rffi.LONG,
    releasegil=ts_call,
    compilation_info=backend.eci)
def c_call_o(space, method, cppobj, nargs, args, cppclass):
    return _c_call_o(method, cppobj, nargs, args, cppclass.handle)

_c_get_methptr_getter = rffi.llexternal(
    "cppyy_get_methptr_getter",
    [C_SCOPE, C_INDEX], C_METHPTRGETTER_PTR,
    releasegil=ts_reflect,
    compilation_info=backend.eci,
    elidable_function=True,
    random_effects_on_gcobjs=False)
def c_get_methptr_getter(space, cppscope, index):
    return _c_get_methptr_getter(cppscope.handle, index)

# handling of function argument buffer ---------------------------------------
_c_allocate_function_args = rffi.llexternal(
    "cppyy_allocate_function_args",
    [rffi.SIZE_T], rffi.VOIDP,
    releasegil=ts_memory,
    compilation_info=backend.eci)
def c_allocate_function_args(space, size):
    return _c_allocate_function_args(size)
_c_deallocate_function_args = rffi.llexternal(
    "cppyy_deallocate_function_args",
    [rffi.VOIDP], lltype.Void,
    releasegil=ts_memory,
    compilation_info=backend.eci)
def c_deallocate_function_args(space, args):
    _c_deallocate_function_args(args)
_c_function_arg_sizeof = rffi.llexternal(
    "cppyy_function_arg_sizeof",
    [], rffi.SIZE_T,
    releasegil=ts_memory,
    compilation_info=backend.eci,
    elidable_function=True,
    random_effects_on_gcobjs=False)
def c_function_arg_sizeof(space):
    return _c_function_arg_sizeof()
_c_function_arg_typeoffset = rffi.llexternal(
    "cppyy_function_arg_typeoffset",
    [], rffi.SIZE_T,
    releasegil=ts_memory,
    compilation_info=backend.eci,
    elidable_function=True,
    random_effects_on_gcobjs=False)
def c_function_arg_typeoffset(space):
    return _c_function_arg_typeoffset()

# scope reflection information -----------------------------------------------
_c_is_namespace = rffi.llexternal(
    "cppyy_is_namespace",
    [C_SCOPE], rffi.INT,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_is_namespace(space, scope):
    return _c_is_namespace(scope)
_c_is_enum = rffi.llexternal(
    "cppyy_is_enum",
    [rffi.CCHARP], rffi.INT,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_is_enum(space, name):
    return _c_is_enum(name)

# type/class reflection information ------------------------------------------
_c_final_name = rffi.llexternal(
    "cppyy_final_name",
    [C_TYPE], rffi.CCHARP,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_final_name(space, cpptype):
    return charp2str_free(space, _c_final_name(cpptype))
_c_scoped_final_name = rffi.llexternal(
    "cppyy_scoped_final_name",
    [C_TYPE], rffi.CCHARP,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_scoped_final_name(space, cpptype):
    return charp2str_free(space, _c_scoped_final_name(cpptype))
_c_has_complex_hierarchy = rffi.llexternal(
    "cppyy_has_complex_hierarchy",
    [C_TYPE], rffi.INT,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_has_complex_hierarchy(space, cpptype):
    return _c_has_complex_hierarchy(cpptype)
_c_num_bases = rffi.llexternal(
    "cppyy_num_bases",
    [C_TYPE], rffi.INT,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_num_bases(space, cppclass):
    return _c_num_bases(cppclass.handle)
_c_base_name = rffi.llexternal(
    "cppyy_base_name",
    [C_TYPE, rffi.INT], rffi.CCHARP,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_base_name(space, cppclass, base_index):
    return charp2str_free(space, _c_base_name(cppclass.handle, base_index))
_c_is_subtype = rffi.llexternal(
    "cppyy_is_subtype",
    [C_TYPE, C_TYPE], rffi.INT,
    releasegil=ts_reflect,
    compilation_info=backend.eci,
    elidable_function=True,
    random_effects_on_gcobjs=False)
@jit.elidable_promote('2')
def c_is_subtype(space, derived, base):
    if derived == base:
        return 1
    return _c_is_subtype(derived.handle, base.handle)

_c_base_offset = rffi.llexternal(
    "cppyy_base_offset",
    [C_TYPE, C_TYPE, C_OBJECT, rffi.INT], rffi.SIZE_T,
    releasegil=ts_reflect,
    compilation_info=backend.eci,
    elidable_function=True,
    random_effects_on_gcobjs=False)
@jit.elidable_promote('1,2,4')
def c_base_offset(space, derived, base, address, direction):
    if derived == base:
        return 0
    return _c_base_offset(derived.handle, base.handle, address, direction)
def c_base_offset1(space, derived_h, base, address, direction):
    return _c_base_offset(derived_h, base.handle, address, direction)

# method/function reflection information -------------------------------------
_c_num_methods = rffi.llexternal(
    "cppyy_num_methods",
    [C_SCOPE], rffi.INT,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_num_methods(space, cppscope):
    return _c_num_methods(cppscope.handle)
_c_method_index_at = rffi.llexternal(
    "cppyy_method_index_at",
    [C_SCOPE, rffi.INT], C_INDEX,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_method_index_at(space, cppscope, imethod):
    return _c_method_index_at(cppscope.handle, imethod)
_c_method_indices_from_name = rffi.llexternal(
    "cppyy_method_indices_from_name",
    [C_SCOPE, rffi.CCHARP], C_INDEX_ARRAY,
    releasegil=ts_reflect,
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
    c_free(rffi.cast(rffi.VOIDP, indices))   # c_free defined below
    return py_indices

_c_method_name = rffi.llexternal(
    "cppyy_method_name",
    [C_SCOPE, C_INDEX], rffi.CCHARP,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_method_name(space, cppscope, index):
    return charp2str_free(space, _c_method_name(cppscope.handle, index))
_c_method_result_type = rffi.llexternal(
    "cppyy_method_result_type",
    [C_SCOPE, C_INDEX], rffi.CCHARP,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_method_result_type(space, cppscope, index):
    return charp2str_free(space, _c_method_result_type(cppscope.handle, index))
_c_method_num_args = rffi.llexternal(
    "cppyy_method_num_args",
    [C_SCOPE, C_INDEX], rffi.INT,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_method_num_args(space, cppscope, index):
    return _c_method_num_args(cppscope.handle, index)
_c_method_req_args = rffi.llexternal(
    "cppyy_method_req_args",
    [C_SCOPE, C_INDEX], rffi.INT,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_method_req_args(space, cppscope, index):
    return _c_method_req_args(cppscope.handle, index)
_c_method_arg_type = rffi.llexternal(
    "cppyy_method_arg_type",
    [C_SCOPE, C_INDEX, rffi.INT], rffi.CCHARP,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_method_arg_type(space, cppscope, index, arg_index):
    return charp2str_free(space, _c_method_arg_type(cppscope.handle, index, arg_index))
_c_method_arg_default = rffi.llexternal(
    "cppyy_method_arg_default",
    [C_SCOPE, C_INDEX, rffi.INT], rffi.CCHARP,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_method_arg_default(space, cppscope, index, arg_index):
    return charp2str_free(space, _c_method_arg_default(cppscope.handle, index, arg_index))
_c_method_signature = rffi.llexternal(
    "cppyy_method_signature",
    [C_SCOPE, C_INDEX], rffi.CCHARP,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_method_signature(space, cppscope, index):
    return charp2str_free(space, _c_method_signature(cppscope.handle, index))

_c_method_is_template = rffi.llexternal(
    "cppyy_method_is_template",
    [C_SCOPE, C_INDEX], rffi.INT,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_method_is_template(space, cppscope, index):
    return _c_method_is_template(cppscope.handle, index)
_c_method_num_template_args = rffi.llexternal(
    "cppyy_method_num_template_args",
    [C_SCOPE, C_INDEX], rffi.INT,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
_c_method_template_arg_name = rffi.llexternal(
    "cppyy_method_template_arg_name",
    [C_SCOPE, C_INDEX, C_INDEX], rffi.CCHARP,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_template_args(space, cppscope, index):
    nargs = _c_method_num_template_args(cppscope.handle, index)
    args = [c_resolve_name(space,
        charp2str_free(space, _c_method_template_arg_name(cppscope.handle, index, iarg)))
        for iarg in range(nargs)]
    return args

_c_get_method = rffi.llexternal(
    "cppyy_get_method",
    [C_SCOPE, C_INDEX], C_METHOD,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_get_method(space, cppscope, index):
    return _c_get_method(cppscope.handle, index)
_c_get_global_operator = rffi.llexternal(
    "cppyy_get_global_operator",
    [C_SCOPE, C_SCOPE, C_SCOPE, rffi.CCHARP], WLAVC_INDEX,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_get_global_operator(space, nss, lc, rc, op):
    if nss is not None:
        return _c_get_global_operator(nss.handle, lc.handle, rc.handle, op)
    return rffi.cast(WLAVC_INDEX, -1)

# method properties ----------------------------------------------------------
_c_is_constructor = rffi.llexternal(
    "cppyy_is_constructor",
    [C_TYPE, C_INDEX], rffi.INT,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_is_constructor(space, cppclass, index):
    return _c_is_constructor(cppclass.handle, index)
_c_is_staticmethod = rffi.llexternal(
    "cppyy_is_staticmethod",
    [C_TYPE, C_INDEX], rffi.INT,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_is_staticmethod(space, cppclass, index):
    return _c_is_staticmethod(cppclass.handle, index)

# data member reflection information -----------------------------------------
_c_num_datamembers = rffi.llexternal(
    "cppyy_num_datamembers",
    [C_SCOPE], rffi.INT,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_num_datamembers(space, cppscope):
    return _c_num_datamembers(cppscope.handle)
_c_datamember_name = rffi.llexternal(
    "cppyy_datamember_name",
    [C_SCOPE, rffi.INT], rffi.CCHARP,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_datamember_name(space, cppscope, datamember_index):
    return charp2str_free(space, _c_datamember_name(cppscope.handle, datamember_index))
_c_datamember_type = rffi.llexternal(
    "cppyy_datamember_type",
    [C_SCOPE, rffi.INT], rffi.CCHARP,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_datamember_type(space, cppscope, datamember_index):
    return charp2str_free(space, _c_datamember_type(cppscope.handle, datamember_index))
_c_datamember_offset = rffi.llexternal(
    "cppyy_datamember_offset",
    [C_SCOPE, rffi.INT], rffi.SIZE_T,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_datamember_offset(space, cppscope, datamember_index):
    return _c_datamember_offset(cppscope.handle, datamember_index)

_c_datamember_index = rffi.llexternal(
    "cppyy_datamember_index",
    [C_SCOPE, rffi.CCHARP], rffi.INT,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_datamember_index(space, cppscope, name):
    return _c_datamember_index(cppscope.handle, name)

# data member properties -----------------------------------------------------
_c_is_publicdata = rffi.llexternal(
    "cppyy_is_publicdata",
    [C_SCOPE, rffi.INT], rffi.INT,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_is_publicdata(space, cppscope, datamember_index):
    return _c_is_publicdata(cppscope.handle, datamember_index)
_c_is_staticdata = rffi.llexternal(
    "cppyy_is_staticdata",
    [C_SCOPE, rffi.INT], rffi.INT,
    releasegil=ts_reflect,
    compilation_info=backend.eci)
def c_is_staticdata(space, cppscope, datamember_index):
    return _c_is_staticdata(cppscope.handle, datamember_index)

# misc helpers ---------------------------------------------------------------
_c_strtoll = rffi.llexternal(
    "cppyy_strtoll",
    [rffi.CCHARP], rffi.LONGLONG,
    releasegil=ts_helper,
    compilation_info=backend.eci)
def c_strtoll(space, svalue):
    return _c_strtoll(svalue)
_c_strtoull = rffi.llexternal(
    "cppyy_strtoull",
    [rffi.CCHARP], rffi.ULONGLONG,
    releasegil=ts_helper,
    compilation_info=backend.eci)
def c_strtoull(space, svalue):
    return _c_strtoull(svalue)
c_free = rffi.llexternal(
    "cppyy_free",
    [rffi.VOIDP], lltype.Void,
    releasegil=ts_memory,
    compilation_info=backend.eci)

def charp2str_free(space, charp):
    string = rffi.charp2str(charp)
    voidp = rffi.cast(rffi.VOIDP, charp)
    c_free(voidp)
    return string

_c_charp2stdstring = rffi.llexternal(
    "cppyy_charp2stdstring",
    [rffi.CCHARP], C_OBJECT,
    releasegil=ts_helper,
    compilation_info=backend.eci)
def c_charp2stdstring(space, svalue):
    with rffi.scoped_view_charp(svalue) as charp:
        result = _c_charp2stdstring(charp)
    return result
_c_stdstring2stdstring = rffi.llexternal(
    "cppyy_stdstring2stdstring",
    [C_OBJECT], C_OBJECT,
    releasegil=ts_helper,
    compilation_info=backend.eci)
def c_stdstring2stdstring(space, cppobject):
    return _c_stdstring2stdstring(cppobject)
