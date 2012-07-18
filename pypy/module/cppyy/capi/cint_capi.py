import py, os, sys

from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.baseobjspace import Wrappable

from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.lltypesystem import rffi
from pypy.rlib import libffi, rdynload

from pypy.module.itertools import interp_itertools


__all__ = ['identify', 'eci', 'c_load_dictionary']

pkgpath = py.path.local(__file__).dirpath().join(os.pardir)
srcpath = pkgpath.join("src")
incpath = pkgpath.join("include")

if os.environ.get("ROOTSYS"):
    import commands
    (stat, incdir) = commands.getstatusoutput("root-config --incdir")
    if stat != 0:        # presumably Reflex-only
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

ts_reflect = False
ts_call    = False
ts_memory  = 'auto'
ts_helper  = 'auto'

# force loading in global mode of core libraries, rather than linking with
# them as PyPy uses various version of dlopen in various places; note that
# this isn't going to fly on Windows (note that locking them in objects and
# calling dlclose in __del__ seems to come too late, so this'll do for now)
with rffi.scoped_str2charp('libCint.so') as ll_libname:
    _cintdll = rdynload.dlopen(ll_libname, rdynload.RTLD_GLOBAL | rdynload.RTLD_NOW)
with rffi.scoped_str2charp('libCore.so') as ll_libname:
    _coredll = rdynload.dlopen(ll_libname, rdynload.RTLD_GLOBAL | rdynload.RTLD_NOW)

eci = ExternalCompilationInfo(
    separate_module_files=[srcpath.join("cintcwrapper.cxx")],
    include_dirs=[incpath] + rootincpath,
    includes=["cintcwrapper.h"],
    library_dirs=rootlibpath,
    link_extra=["-lCore", "-lCint"],
    use_cpp_linker=True,
)

_c_load_dictionary = rffi.llexternal(
    "cppyy_load_dictionary",
    [rffi.CCHARP], rdynload.DLLHANDLE,
    threadsafe=False,
    compilation_info=eci)

def c_load_dictionary(name):
    result = _c_load_dictionary(name)
    if not result:
        err = rdynload.dlerror()
        raise rdynload.DLOpenError(err)
    return libffi.CDLL(name)       # should return handle to already open file


# CINT-specific pythonizations ===============================================

### TTree --------------------------------------------------------------------
_ttree_Branch = rffi.llexternal(
    "cppyy_ttree_Branch",
    [rffi.VOIDP, rffi.CCHARP, rffi.CCHARP, rffi.VOIDP, rffi.INT, rffi.INT], rffi.LONG,
    threadsafe=False,
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
        except OperationError:
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
        w_branch = interp_cppyy.wrap_cppobject(
            space, space.w_None, branch_class, vbranch, isref=False, python_owns=False)
        return w_branch
    except (OperationError, TypeError, IndexError), e:
        pass

    # return control back to the original, unpythonized overload
    return tree_class.get_overload("Branch").call(w_self, args_w)

class W_TTreeIter(Wrappable):
    def __init__(self, space, w_tree):
        self.current = 0
        self.w_tree = w_tree
        from pypy.module.cppyy import interp_cppyy
        tree = space.interp_w(interp_cppyy.W_CPPInstance, self.w_tree)
        self.tree = tree.get_cppthis(tree.cppclass)
        self.getentry = tree.cppclass.get_overload("GetEntry").functions[0]

        # setup data members if this is the first iteration time
        try:
            space.getattr(w_tree, space.wrap("_pythonized"))
        except OperationError:
            self.space = space = tree.space       # holds the class cache in State
            w_branches = space.call_method(w_tree, "GetListOfBranches")
            for i in range(space.int_w(space.call_method(w_branches, "GetEntriesFast"))):
                w_branch = space.call_method(w_branches, "At", space.wrap(i))
                w_name = space.call_method(w_branch, "GetName")
                w_klassname = space.call_method(w_branch, "GetClassName")
                klass = interp_cppyy.scope_byname(space, space.str_w(w_klassname))
                w_obj = klass.construct()
                space.call_method(w_branch, "SetObject", w_obj)
                # cache the object and define this tree pythonized
                space.setattr(w_tree, w_name, w_obj)
                space.setattr(w_tree, space.wrap("_pythonized"), space.w_True)

    def iter_w(self):
        return self.space.wrap(self)

    def next_w(self):
        w_bytes_read = self.getentry.call(self.tree, [self.space.wrap(self.current)])
        if not self.space.is_true(w_bytes_read):
            raise OperationError(self.space.w_StopIteration, self.space.w_None)
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

    ### TTree
    _pythonizations['ttree_Branch'] = space.wrap(interp2app(ttree_Branch))
    _pythonizations['ttree_iter']   = space.wrap(interp2app(ttree_iter))

# callback coming in when app-level bound classes have been created
def pythonize(space, name, w_pycppclass):

    if name == 'TFile':
        space.setattr(w_pycppclass, space.wrap("__getattr__"),
                      space.getattr(w_pycppclass, space.wrap("Get")))

    elif name == 'TTree':
        space.setattr(w_pycppclass, space.wrap("_unpythonized_Branch"),
                      space.getattr(w_pycppclass, space.wrap("Branch")))
        space.setattr(w_pycppclass, space.wrap("Branch"), _pythonizations["ttree_Branch"])
        space.setattr(w_pycppclass, space.wrap("__iter__"), _pythonizations["ttree_iter"])

    elif name[0:8] == "TVectorT":    # TVectorT<> template
        space.setattr(w_pycppclass, space.wrap("__len__"),
                      space.getattr(w_pycppclass, space.wrap("GetNoElements")))
