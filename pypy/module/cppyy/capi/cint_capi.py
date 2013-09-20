import py, os, sys

from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.baseobjspace import W_Root

from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib import libffi, rdynload

from pypy.module.cppyy.capi.capi_types import C_OBJECT


__all__ = ['identify', 'std_string_name', 'eci', 'c_load_dictionary']

pkgpath = py.path.local(__file__).dirpath().join(os.pardir)
srcpath = pkgpath.join("src")
incpath = pkgpath.join("include")

if os.environ.get("ROOTSYS"):
    import commands
    (stat, incdir) = commands.getstatusoutput("root-config --incdir")
    if stat != 0:
        rootincpath = [os.path.join(os.environ["ROOTSYS"], "include")]
        rootlibpath = [os.path.join(os.environ["ROOTSYS"], "lib64"), os.path.join(os.environ["ROOTSYS"], "lib")]
    else:
        rootincpath = [incdir]
        rootlibpath = commands.getoutput("root-config --libdir").split()
else:
    rootincpath = []
    rootlibpath = []

def identify():
    return 'CINT'

ts_reflect = True
ts_call    = True
ts_memory  = False
ts_helper  = False

std_string_name = 'string'

# force loading in global mode of core libraries, rather than linking with
# them as PyPy uses various version of dlopen in various places; note that
# this isn't going to fly on Windows (note that locking them in objects and
# calling dlclose in __del__ seems to come too late, so this'll do for now)
with rffi.scoped_str2charp('libCint.so') as ll_libname:
    _cintdll = rdynload.dlopen(ll_libname, rdynload.RTLD_GLOBAL | rdynload.RTLD_NOW)
with rffi.scoped_str2charp('libCore.so') as ll_libname:
    _coredll = rdynload.dlopen(ll_libname, rdynload.RTLD_GLOBAL | rdynload.RTLD_NOW)
with rffi.scoped_str2charp('libHist.so') as ll_libname:
    _coredll = rdynload.dlopen(ll_libname, rdynload.RTLD_GLOBAL | rdynload.RTLD_NOW)

eci = ExternalCompilationInfo(
    separate_module_files=[srcpath.join("cintcwrapper.cxx")],
    include_dirs=[incpath] + rootincpath,
    includes=["cintcwrapper.h"],
    library_dirs=rootlibpath,
    libraries=["Hist", "Core", "Cint"],
    use_cpp_linker=True,
)

_c_load_dictionary = rffi.llexternal(
    "cppyy_load_dictionary",
    [rffi.CCHARP], rdynload.DLLHANDLE,
    releasegil=False,
    compilation_info=eci)

def c_load_dictionary(name):
    result = _c_load_dictionary(name)
    # ignore result: libffi.CDLL(name) either returns a handle to the already
    # open file, or will fail as well and produce a correctly formatted error
    return libffi.CDLL(name)


# CINT-specific pythonizations ===============================================
_c_charp2TString = rffi.llexternal(
    "cppyy_charp2TString",
    [rffi.CCHARP], C_OBJECT,
    releasegil=ts_helper,
    compilation_info=eci)
def c_charp2TString(space, svalue):
    charp = rffi.str2charp(svalue)
    result = _c_charp2TString(charp)
    rffi.free_charp(charp)
    return result
_c_TString2TString = rffi.llexternal(
    "cppyy_TString2TString",
    [C_OBJECT], C_OBJECT,
    releasegil=ts_helper,
    compilation_info=eci)
def c_TString2TString(space, cppobject):
    return _c_TString2TString(cppobject)

def _get_string_data(space, w_obj, m1, m2 = None):
    from pypy.module.cppyy import interp_cppyy
    obj = space.interp_w(interp_cppyy.W_CPPInstance, w_obj)
    w_1 = obj.space.call_method(w_obj, m1)
    if m2 is None:
        return w_1
    return obj.space.call_method(w_1, m2)

### TF1 ----------------------------------------------------------------------
class State(object):
    def __init__(self, space):
        self.tfn_pyfuncs = []
        self.tfn_callbacks = []

_create_tf1 = rffi.llexternal(
    "cppyy_create_tf1",
    [rffi.CCHARP, rffi.ULONG, rffi.DOUBLE, rffi.DOUBLE, rffi.INT], C_OBJECT,
    releasegil=False,
    compilation_info=eci)

@unwrap_spec(args_w='args_w')
def tf1_tf1(space, w_self, args_w):
    """Pythonized version of TF1 constructor:
    takes functions and callable objects, and allows a callback into them."""

    from pypy.module.cppyy import interp_cppyy
    tf1_class = interp_cppyy.scope_byname(space, "TF1")

    # expected signature:
    #  1. (char* name, pyfunc, double xmin, double xmax, int npar = 0)
    argc = len(args_w)

    try:
        # Note: argcount is +1 for the class (== w_self)
        if argc < 5 or 6 < argc:
            raise TypeError("wrong number of arguments")

        # second argument must be a name
        funcname = space.str_w(args_w[1])

        # last (optional) argument is number of parameters
        npar = 0
        if argc == 6: npar = space.int_w(args_w[5])

        # third argument must be a callable python object
        w_callable = args_w[2]
        if not space.is_true(space.callable(w_callable)):
            raise TypeError("2nd argument is not a valid python callable")

        # generate a pointer to function
        from pypy.module._cffi_backend import newtype, ctypefunc, func

        c_double  = newtype.new_primitive_type(space, 'double')
        c_doublep = newtype.new_pointer_type(space, c_double)

        # wrap the callable as the signature needs modifying
        w_ifunc = interp_cppyy.get_interface_func(space, w_callable, npar)

        w_cfunc = ctypefunc.W_CTypeFunc(space, [c_doublep, c_doublep], c_double, False)
        w_callback = func.callback(space, w_cfunc, w_ifunc, None)
        funcaddr = rffi.cast(rffi.ULONG, w_callback.get_closure())

        # so far, so good; leaves on issue: CINT is expecting a wrapper, but
        # we need the overload that takes a function pointer, which is not in
        # the dictionary, hence this helper:
        newinst = _create_tf1(space.str_w(args_w[1]), funcaddr,
                      space.float_w(args_w[3]), space.float_w(args_w[4]), npar)
 
        from pypy.module.cppyy import interp_cppyy
        w_instance = interp_cppyy.wrap_cppobject(space, newinst, tf1_class,
                                      do_cast=False, python_owns=True, fresh=True)

        # tie all the life times to the TF1 instance
        space.setattr(w_instance, space.wrap('_callback'), w_callback)

        return w_instance
    except (OperationError, TypeError, IndexError), e:
        newargs_w = args_w[1:]     # drop class

    # return control back to the original, unpythonized overload
    ol = tf1_class.get_overload("TF1")
    return ol.call(None, newargs_w)

### TTree --------------------------------------------------------------------
_ttree_Branch = rffi.llexternal(
    "cppyy_ttree_Branch",
    [rffi.VOIDP, rffi.CCHARP, rffi.CCHARP, rffi.VOIDP, rffi.INT, rffi.INT], rffi.LONG,
    releasegil=False,
    compilation_info=eci)

@unwrap_spec(args_w='args_w')
def ttree_Branch(space, w_self, args_w):
    """Pythonized version of TTree::Branch(): takes proxy objects and by-passes
    the CINT-manual layer."""

    from pypy.module.cppyy import interp_cppyy
    tree_class = interp_cppyy.scope_byname(space, "TTree")

    # sigs to modify (and by-pass CINT):
    #  1. (const char*, const char*, T**,               Int_t=32000, Int_t=99)
    #  2. (const char*, T**,                            Int_t=32000, Int_t=99)
    argc = len(args_w)

    # basic error handling of wrong arguments is best left to the original call,
    # so that error messages etc. remain consistent in appearance: the following
    # block may raise TypeError or IndexError to break out anytime

    try:
        if argc < 2 or 5 < argc:
            raise TypeError("wrong number of arguments")

        tree = space.interp_w(interp_cppyy.W_CPPInstance, w_self, can_be_None=True)
        if (tree is None) or (tree.cppclass != tree_class):
            raise TypeError("not a TTree")

        # first argument must always always be cont char*
        branchname = space.str_w(args_w[0])

        # if args_w[1] is a classname, then case 1, else case 2
        try:
            classname = space.str_w(args_w[1])
            addr_idx  = 2
            w_address = args_w[addr_idx]
        except (OperationError, TypeError):
            addr_idx  = 1
            w_address = args_w[addr_idx]

        bufsize, splitlevel = 32000, 99
        if addr_idx+1 < argc: bufsize = space.c_int_w(args_w[addr_idx+1])
        if addr_idx+2 < argc: splitlevel = space.c_int_w(args_w[addr_idx+2])

        # now retrieve the W_CPPInstance and build other stub arguments
        space = tree.space    # holds the class cache in State
        cppinstance = space.interp_w(interp_cppyy.W_CPPInstance, w_address)
        address = rffi.cast(rffi.VOIDP, cppinstance.get_rawobject())
        klassname = cppinstance.cppclass.full_name()
        vtree = rffi.cast(rffi.VOIDP, tree.get_rawobject())

        # call the helper stub to by-pass CINT
        vbranch = _ttree_Branch(vtree, branchname, klassname, address, bufsize, splitlevel)
        branch_class = interp_cppyy.scope_byname(space, "TBranch")
        w_branch = interp_cppyy.wrap_cppobject(space, vbranch, branch_class)
        return w_branch
    except (OperationError, TypeError, IndexError):
        pass

    # return control back to the original, unpythonized overload
    ol = tree_class.get_overload("Branch")
    return ol.call(w_self, args_w)

def activate_branch(space, w_branch):
    w_branches = space.call_method(w_branch, "GetListOfBranches")
    for i in range(space.int_w(space.call_method(w_branches, "GetEntriesFast"))):
        w_b = space.call_method(w_branches, "At", space.wrap(i))
        activate_branch(space, w_b)
    space.call_method(w_branch, "SetStatus", space.wrap(1))
    space.call_method(w_branch, "ResetReadEntry")

c_ttree_GetEntry = rffi.llexternal(
    "cppyy_ttree_GetEntry",
    [rffi.VOIDP, rffi.LONGLONG], rffi.LONGLONG,
    releasegil=False,
    compilation_info=eci)

@unwrap_spec(args_w='args_w')
def ttree_getattr(space, w_self, args_w):
    """Specialized __getattr__ for TTree's that allows switching on/off the
    reading of individual branchs."""

    from pypy.module.cppyy import interp_cppyy
    tree = space.interp_w(interp_cppyy.W_CPPInstance, w_self)

    space = tree.space            # holds the class cache in State

    # prevent recursion
    attr = space.str_w(args_w[0])
    if attr and attr[0] == '_':
        raise OperationError(space.w_AttributeError, args_w[0])

    # try the saved cdata (for builtin types)
    try:
        w_cdata = space.getattr(w_self, space.wrap('_'+attr))
        from pypy.module._cffi_backend import cdataobj
        cdata = space.interp_w(cdataobj.W_CData, w_cdata, can_be_None=False)
        return cdata.convert_to_object()
    except OperationError:
        pass

    # setup branch as a data member and enable it for reading
    w_branch = space.call_method(w_self, "GetBranch", args_w[0])
    if not space.is_true(w_branch):
        raise OperationError(space.w_AttributeError, args_w[0])
    activate_branch(space, w_branch)

    # figure out from where we're reading
    entry = space.int_w(space.call_method(w_self, "GetReadEntry"))
    if entry == -1:
        entry = 0

    # setup cache structure
    w_klassname = space.call_method(w_branch, "GetClassName")
    if space.is_true(w_klassname):
        # some instance
        klass = interp_cppyy.scope_byname(space, space.str_w(w_klassname))
        w_obj = klass.construct()
        space.call_method(w_branch, "SetObject", w_obj)
        space.call_method(w_branch, "GetEntry", space.wrap(entry))
        space.setattr(w_self, args_w[0], w_obj)
        return w_obj
    else:
        # builtin data
        w_leaf = space.call_method(w_self, "GetLeaf", args_w[0])
        space.call_method(w_branch, "GetEntry", space.wrap(entry))

        # location
        w_address = space.call_method(w_leaf, "GetValuePointer")
        buf = space.buffer_w(w_address)
        from pypy.module._rawffi import buffer
        assert isinstance(buf, buffer.RawFFIBuffer)
        address = rffi.cast(rffi.CCHARP, buf.datainstance.ll_buffer)

        # placeholder
        w_typename = space.call_method(w_leaf, "GetTypeName" )
        from pypy.module.cppyy import capi
        typename = capi.c_resolve_name(space, space.str_w(w_typename))
        if typename == 'bool': typename = '_Bool'
        w_address = space.call_method(w_leaf, "GetValuePointer")
        from pypy.module._cffi_backend import cdataobj, newtype
        cdata = cdataobj.W_CData(space, address, newtype.new_primitive_type(space, typename))

        # cache result
        space.setattr(w_self, space.wrap('_'+attr), space.wrap(cdata))
        return space.getattr(w_self, args_w[0])

class W_TTreeIter(W_Root):
    def __init__(self, space, w_tree):
        from pypy.module.cppyy import interp_cppyy
        tree = space.interp_w(interp_cppyy.W_CPPInstance, w_tree)
        self.vtree = rffi.cast(rffi.VOIDP, tree.get_cppthis(tree.cppclass))
        self.w_tree = w_tree

        self.current  = 0
        self.maxentry = space.int_w(space.call_method(w_tree, "GetEntriesFast"))

        space = self.space = tree.space          # holds the class cache in State
        space.call_method(w_tree, "SetBranchStatus", space.wrap("*"), space.wrap(0))

    def iter_w(self):
        return self.space.wrap(self)

    def next_w(self):
        if self.current == self.maxentry:
            raise OperationError(self.space.w_StopIteration, self.space.w_None)
        # TODO: check bytes read?
        c_ttree_GetEntry(self.vtree, self.current)
        self.current += 1 
        return self.w_tree

W_TTreeIter.typedef = TypeDef(
    'TTreeIter',
    __iter__ = interp2app(W_TTreeIter.iter_w),
    next = interp2app(W_TTreeIter.next_w),
)

def ttree_iter(space, w_self):
    """Allow iteration over TTree's. Also initializes branch data members and
    sets addresses, if needed."""
    w_treeiter = W_TTreeIter(space, w_self)
    return w_treeiter

# setup pythonizations for later use at run-time
_pythonizations = {}
def register_pythonizations(space):
    "NOT_RPYTHON"

    allfuncs = [

        ### TF1
        tf1_tf1,

        ### TTree
        ttree_Branch, ttree_iter, ttree_getattr,
    ]

    for f in allfuncs:
        _pythonizations[f.__name__] = space.wrap(interp2app(f))

def _method_alias(space, w_pycppclass, m1, m2):
    space.setattr(w_pycppclass, space.wrap(m1),
                  space.getattr(w_pycppclass, space.wrap(m2)))

# callback coming in when app-level bound classes have been created
def pythonize(space, name, w_pycppclass):

    if name == "TCollection":
        _method_alias(space, w_pycppclass, "append", "Add")
        _method_alias(space, w_pycppclass, "__len__", "GetSize")

    elif name == "TF1":
        space.setattr(w_pycppclass, space.wrap("__new__"), _pythonizations["tf1_tf1"])

    elif name == "TFile":
        _method_alias(space, w_pycppclass, "__getattr__", "Get")

    elif name == "TObjString":
        _method_alias(space, w_pycppclass, "__str__", "GetName")
        _method_alias(space, w_pycppclass, "_cppyy_as_builtin", "GetString")

    elif name == "TString":
        _method_alias(space, w_pycppclass, "__str__", "Data")
        _method_alias(space, w_pycppclass, "__len__", "Length")
        _method_alias(space, w_pycppclass, "__cmp__", "CompareTo")
        _method_alias(space, w_pycppclass, "_cppyy_as_builtin", "Data")

    elif name == "TTree":
        _method_alias(space, w_pycppclass, "_unpythonized_Branch", "Branch")

        space.setattr(w_pycppclass, space.wrap("Branch"),      _pythonizations["ttree_Branch"])
        space.setattr(w_pycppclass, space.wrap("__iter__"),    _pythonizations["ttree_iter"])
        space.setattr(w_pycppclass, space.wrap("__getattr__"), _pythonizations["ttree_getattr"])

    elif name[0:8] == "TVectorT":    # TVectorT<> template
        _method_alias(space, w_pycppclass, "__len__", "GetNoElements")

# destruction callback (needs better solution, but this is for CINT
# only and should not appear outside of ROOT-specific uses)
from pypy.module.cpyext.api import cpython_api, CANNOT_FAIL

@cpython_api([rffi.VOIDP], lltype.Void, error=CANNOT_FAIL)
def cppyy_recursive_remove(space, cppobject):
    from pypy.module.cppyy.interp_cppyy import memory_regulator
    from pypy.module.cppyy.capi import C_OBJECT, C_NULL_OBJECT

    obj = memory_regulator.retrieve(rffi.cast(C_OBJECT, cppobject))
    if obj is not None:
        memory_regulator.unregister(obj)
        obj._rawobject = C_NULL_OBJECT
