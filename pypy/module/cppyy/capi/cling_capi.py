import py, os

from pypy.objspace.std.iterobject import W_AbstractSeqIterObject

from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import interp2app

from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib.rarithmetic import intmask
from rpython.rlib import jit, libffi, rdynload

from pypy.module._rawffi.array import W_ArrayInstance
from pypy.module.cppyy.capi.capi_types import C_OBJECT

__all__ = ['identify', 'std_string_name', 'eci', 'c_load_dictionary']

pkgpath = py.path.local(__file__).dirpath().join(os.pardir)
srcpath = pkgpath.join("src")
incpath = pkgpath.join("include")

import commands
(config_stat, incdir) = commands.getstatusoutput("root-config --incdir")

if os.environ.get("ROOTSYS"):
    if config_stat != 0:     # presumably Reflex-only
        rootincpath = [os.path.join(os.environ["ROOTSYS"], "interpreter/cling/include"),
                       os.path.join(os.environ["ROOTSYS"], "interpreter/llvm/inst/include"),
                       os.path.join(os.environ["ROOTSYS"], "include"),]
        rootlibpath = [os.path.join(os.environ["ROOTSYS"], "lib64"), os.path.join(os.environ["ROOTSYS"], "lib")]
    else:
        rootincpath = [incdir]
        rootlibpath = commands.getoutput("root-config --libdir").split()
else:
    if config_stat == 0:
        rootincpath = [incdir]
        rootlibpath = commands.getoutput("root-config --libdir").split()
    else:
        rootincpath = []
        rootlibpath = []

def identify():
    return 'Cling'

ts_reflect = False
ts_call    = 'auto'
ts_memory  = 'auto'
ts_helper  = 'auto'

std_string_name = 'std::basic_string<char>'

# force loading (and exposure) of libCore symbols
with rffi.scoped_str2charp('libCore.so') as ll_libname:
    _coredll = rdynload.dlopen(ll_libname, rdynload.RTLD_GLOBAL | rdynload.RTLD_NOW)

# require local translator path to pickup common defs
from rpython.translator import cdir
translator_c_dir = py.path.local(cdir)

eci = ExternalCompilationInfo(
    separate_module_files=[srcpath.join("clingcwrapper.cxx")],
    include_dirs=[incpath, translator_c_dir] + rootincpath,
    includes=["clingcwrapper.h"],
    library_dirs=rootlibpath,
    libraries=["Cling"],
    compile_extra=["-fno-strict-aliasing", "-std=c++14"],
    use_cpp_linker=True,
)

_c_load_dictionary = rffi.llexternal(
    "cppyy_load_dictionary",
    [rffi.CCHARP], rdynload.DLLHANDLE,
    releasegil=False,
    compilation_info=eci)

def c_load_dictionary(name):
    pch = _c_load_dictionary(name)
    return pch

_c_stdstring2charp = rffi.llexternal(
    "cppyy_stdstring2charp",
    [C_OBJECT, rffi.SIZE_TP], rffi.CCHARP,
    releasegil=ts_helper,
    compilation_info=eci)
def c_stdstring2charp(space, cppstr):
    sz = lltype.malloc(rffi.SIZE_TP.TO, 1, flavor='raw')
    try:
        cstr = _c_stdstring2charp(cppstr, sz)
        cstr_len = intmask(sz[0])
    finally:
        lltype.free(sz, flavor='raw')
    return rffi.charpsize2str(cstr, cstr_len)

# TODO: factor these out ...
# pythonizations

#
# std::string behavior
def stdstring_c_str(space, w_self):
    """Return a python string taking into account \0"""

    from pypy.module.cppyy import interp_cppyy
    cppstr = space.interp_w(interp_cppyy.W_CPPInstance, w_self, can_be_None=False)
    return space.wrap(c_stdstring2charp(space, cppstr._rawobject))

#
# std::vector behavior
class W_STLVectorIter(W_AbstractSeqIterObject):
    _immutable_fields_ = ['overload', 'len']#'data', 'converter', 'len', 'stride', 'vector']

    def __init__(self, space, w_vector):
        W_AbstractSeqIterObject.__init__(self, w_vector)
        # TODO: this should live in rpythonize.py or something so that the
        # imports can move to the top w/o getting circles
        from pypy.module.cppyy import interp_cppyy
        assert isinstance(w_vector, interp_cppyy.W_CPPInstance)
        vector = space.interp_w(interp_cppyy.W_CPPInstance, w_vector)
        self.overload = vector.cppclass.get_overload("__getitem__")

        from pypy.module.cppyy import capi
        v_type = capi.c_stdvector_valuetype(space, vector.cppclass.name)
        v_size = capi.c_stdvector_valuesize(space, vector.cppclass.name)

        if not v_type or not v_size:
            raise NotImplementedError   # fallback on getitem

        w_arr = vector.cppclass.get_overload("data").call(w_vector, [])
        arr = space.interp_w(W_ArrayInstance, w_arr, can_be_None=True)
        if not arr:
            raise OperationError(space.w_StopIteration, space.w_None)

        self.data = rffi.cast(rffi.VOIDP, space.uint_w(arr.getbuffer(space)))

        from pypy.module.cppyy import converter
        self.converter = converter.get_converter(space, v_type, '')
        self.len     = space.uint_w(vector.cppclass.get_overload("size").call(w_vector, []))
        self.stride  = v_size

    def descr_next(self, space):
        if self.w_seq is None:
            raise OperationError(space.w_StopIteration, space.w_None)
        if self.len <= self.index:
            self.w_seq = None
            raise OperationError(space.w_StopIteration, space.w_None)
        try:
            from pypy.module.cppyy import capi    # TODO: refector
            offset = capi.direct_ptradd(rffi.cast(C_OBJECT, self.data), self.index*self.stride)
            w_item = self.converter.from_memory(space, space.w_None, space.w_None, offset)
        except OperationError as e:
            self.w_seq = None
            if not e.match(space, space.w_IndexError):
                raise
            raise OperationError(space.w_StopIteration, space.w_None)
        self.index += 1
        return w_item

def stdvector_iter(space, w_self):
    return W_STLVectorIter(space, w_self)

# setup pythonizations for later use at run-time
_pythonizations = {}
def register_pythonizations(space):
    "NOT_RPYTHON"

    allfuncs = [

        ### std::string
        stdstring_c_str,

        ### std::vector
        stdvector_iter,

    ]

    for f in allfuncs:
        _pythonizations[f.__name__] = space.wrap(interp2app(f))

def _method_alias(space, w_pycppclass, m1, m2):
    space.setattr(w_pycppclass, space.wrap(m1),
                  space.getattr(w_pycppclass, space.wrap(m2)))

def pythonize(space, name, w_pycppclass):
    if name == "string":
        space.setattr(w_pycppclass, space.wrap("c_str"), _pythonizations["stdstring_c_str"])
        _method_alias(space, w_pycppclass, "_cppyy_as_builtin", "c_str")
        _method_alias(space, w_pycppclass, "__str__",           "c_str")

    if "vector" in name[:11]: # len('std::vector') == 11
        from pypy.module.cppyy import capi
        v_type = capi.c_stdvector_valuetype(space, name)
        if v_type:
            space.setattr(w_pycppclass, space.wrap("value_type"), space.wrap(v_type))
        v_size = capi.c_stdvector_valuesize(space, name)
        if v_size:
            space.setattr(w_pycppclass, space.wrap("value_size"), space.wrap(v_size))
        space.setattr(w_pycppclass, space.wrap("__iter__"), _pythonizations["stdvector_iter"])
