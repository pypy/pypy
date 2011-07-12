import py, os

from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.lltypesystem import rffi, lltype

pkgpath = py.path.local(__file__).dirpath().join(os.pardir)
srcpath = pkgpath.join("src")
incpath = pkgpath.join("include")

if os.environ.get("ROOTSYS"):
    rootincpath = [os.path.join(os.environ["ROOTSYS"], "include")]
    rootlibpath = [os.path.join(os.environ["ROOTSYS"], "lib")]
else:
    rootincpath = []
    rootlibpath = []

eci = ExternalCompilationInfo(
    separate_module_files=[srcpath.join("reflexcwrapper.cxx")],
    include_dirs=[incpath] + rootincpath,
    includes=["reflexcwrapper.h"],
    library_dirs=rootlibpath,
    libraries=["Reflex"],
    use_cpp_linker=True,
)

C_TYPEHANDLE = rffi.VOIDP
C_OBJECT = rffi.VOIDP

C_METHPTRGETTER = lltype.FuncType([C_OBJECT], rffi.VOIDP)
C_METHPTRGETTER_PTR = lltype.Ptr(C_METHPTRGETTER)

c_get_typehandle = rffi.llexternal(
    "cppyy_get_typehandle",
    [rffi.CCHARP], C_TYPEHANDLE,
    compilation_info=eci)

c_get_templatehandle = rffi.llexternal(
    "cppyy_get_templatehandle",
    [rffi.CCHARP], C_TYPEHANDLE,
    compilation_info=eci)

c_allocate = rffi.llexternal(
    "cppyy_allocate",
    [C_TYPEHANDLE], rffi.VOIDP,
    compilation_info=eci)
c_deallocate = rffi.llexternal(
    "cppyy_deallocate",
    [C_TYPEHANDLE, C_OBJECT], lltype.Void,
    compilation_info=eci)

c_destruct = rffi.llexternal(
    "cppyy_destruct",
    [C_TYPEHANDLE, C_OBJECT], lltype.Void,
    compilation_info=eci)


c_is_namespace = rffi.llexternal(
    "cppyy_is_namespace",
    [C_TYPEHANDLE], rffi.INT,
    compilation_info=eci)


c_final_name = rffi.llexternal(
    "cppyy_final_name",
    [C_TYPEHANDLE], rffi.CCHARP,
    compilation_info=eci)

c_num_bases = rffi.llexternal(
    "cppyy_num_bases",
    [C_TYPEHANDLE], rffi.INT,
    compilation_info=eci)

c_base_name = rffi.llexternal(
    "cppyy_base_name",
    [C_TYPEHANDLE, rffi.INT], rffi.CCHARP,
    compilation_info=eci)

c_is_subtype = rffi.llexternal(
    "cppyy_is_subtype",
    [C_TYPEHANDLE, C_TYPEHANDLE], rffi.INT,
    compilation_info=eci,
    elidable_function=True)
c_base_offset = rffi.llexternal(
    "cppyy_base_offset",
    [C_TYPEHANDLE, C_TYPEHANDLE], rffi.SIZE_T,
    compilation_info=eci,
    elidable_function=True)


c_call_v = rffi.llexternal(
    "cppyy_call_v",
    [C_TYPEHANDLE, rffi.INT, C_OBJECT, rffi.INT, rffi.VOIDPP], lltype.Void,
    compilation_info=eci)
c_call_o = rffi.llexternal(
    "cppyy_call_o",
    [C_TYPEHANDLE, rffi.INT, C_OBJECT, rffi.INT, rffi.VOIDPP, C_TYPEHANDLE], rffi.LONG,
    compilation_info=eci)
c_call_b = rffi.llexternal(
    "cppyy_call_b",
    [C_TYPEHANDLE, rffi.INT, C_OBJECT, rffi.INT, rffi.VOIDPP], rffi.INT,
    compilation_info=eci)
c_call_c = rffi.llexternal(
    "cppyy_call_c",
    [C_TYPEHANDLE, rffi.INT, C_OBJECT, rffi.INT, rffi.VOIDPP], rffi.CHAR,
    compilation_info=eci)
c_call_h = rffi.llexternal(
    "cppyy_call_h",
    [C_TYPEHANDLE, rffi.INT, C_OBJECT, rffi.INT, rffi.VOIDPP], rffi.SHORT,
    compilation_info=eci)
c_call_i = rffi.llexternal(
    "cppyy_call_i",
    [C_TYPEHANDLE, rffi.INT, C_OBJECT, rffi.INT, rffi.VOIDPP], rffi.INT,
    compilation_info=eci)
c_call_l = rffi.llexternal(
    "cppyy_call_l",
    [C_TYPEHANDLE, rffi.INT, C_OBJECT, rffi.INT, rffi.VOIDPP], rffi.LONG,
    compilation_info=eci)
c_call_f = rffi.llexternal(
    "cppyy_call_f",
    [C_TYPEHANDLE, rffi.INT, C_OBJECT, rffi.INT, rffi.VOIDPP], rffi.DOUBLE,
    compilation_info=eci)
c_call_d = rffi.llexternal(
    "cppyy_call_d",
    [C_TYPEHANDLE, rffi.INT, C_OBJECT, rffi.INT, rffi.VOIDPP], rffi.DOUBLE,
    compilation_info=eci)


c_get_methptr_getter = rffi.llexternal(
    "cppyy_get_methptr_getter",
    [C_TYPEHANDLE, rffi.INT], C_METHPTRGETTER_PTR,
    compilation_info=eci)


c_num_methods = rffi.llexternal(
    "cppyy_num_methods",
    [C_TYPEHANDLE], rffi.INT,
    compilation_info=eci)
c_method_name = rffi.llexternal(
    "cppyy_method_name",
    [C_TYPEHANDLE, rffi.INT], rffi.CCHARP,
    compilation_info=eci)
c_method_result_type = rffi.llexternal(
    "cppyy_method_result_type",
    [C_TYPEHANDLE, rffi.INT], rffi.CCHARP,
    compilation_info=eci)
c_method_num_args = rffi.llexternal(
    "cppyy_method_num_args",
    [C_TYPEHANDLE, rffi.INT], rffi.INT,
    compilation_info=eci)
c_method_req_args = rffi.llexternal(
    "cppyy_method_req_args",
    [C_TYPEHANDLE, rffi.INT], rffi.INT,
    compilation_info=eci)
c_method_arg_type = rffi.llexternal(
    "cppyy_method_arg_type",
    [C_TYPEHANDLE, rffi.INT, rffi.INT], rffi.CCHARP,
    compilation_info=eci)

c_is_constructor = rffi.llexternal(
    "cppyy_is_constructor",
    [C_TYPEHANDLE, rffi.INT], rffi.INT,
    compilation_info=eci)
c_is_staticmethod = rffi.llexternal(
    "cppyy_is_staticmethod",
    [C_TYPEHANDLE, rffi.INT], rffi.INT,
    compilation_info=eci)

c_num_data_members = rffi.llexternal(
    "cppyy_num_data_members",
    [C_TYPEHANDLE], rffi.INT,
    compilation_info=eci)
c_data_member_name = rffi.llexternal(
    "cppyy_data_member_name",
    [C_TYPEHANDLE, rffi.INT], rffi.CCHARP,
    compilation_info=eci)
c_data_member_type = rffi.llexternal(
    "cppyy_data_member_type",
    [C_TYPEHANDLE, rffi.INT], rffi.CCHARP,
    compilation_info=eci)
c_data_member_offset = rffi.llexternal(
    "cppyy_data_member_offset",
    [C_TYPEHANDLE, rffi.INT], rffi.SIZE_T,
    compilation_info=eci)

c_is_staticdata = rffi.llexternal(
    "cppyy_is_staticdata",
    [C_TYPEHANDLE, rffi.INT], rffi.INT,
    compilation_info=eci)

c_free = rffi.llexternal(
    "cppyy_free",
    [rffi.VOIDP], lltype.Void,
    compilation_info=eci)

def charp2str_free(charp):
    string = rffi.charp2str(charp)
    voidp = rffi.cast(rffi.VOIDP, charp)
    c_free(voidp)
    return string
