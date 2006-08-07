from pypy.rpython.rtyper import inputconst
from pypy.rpython.rctypes.rmodel import CTypesValueRepr, CTypesRefRepr
from pypy.rpython.rctypes.afunc import CFuncPtrType
from pypy.rpython.error import TyperError
from pypy.rpython.lltypesystem import lltype
from pypy.annotation import model as annmodel
from pypy.annotation.model import SomeCTypesObject
from pypy.objspace.flow.model import Constant

import ctypes


class CFuncPtrRepr(CTypesValueRepr):

    def __init__(self, rtyper, s_funcptr):
        # For recursive types, getting the args_r and r_result is delayed
        # until _setup_repr().
        ll_contents = lltype.Ptr(lltype.ForwardReference())
        super(CFuncPtrRepr, self).__init__(rtyper, s_funcptr, ll_contents)
        self.sample = self.ctype()
        self.argtypes = self.sample.argtypes
        self.restype = self.sample.restype
        if self.argtypes is None:
            raise TyperError("cannot handle yet function pointers with "
                             "unspecified argument types")

    def _setup_repr(self):
        # Find the repr and low-level type of the arguments and return value
        rtyper = self.rtyper
        args_r = []
        for arg_ctype in self.argtypes:
            r = rtyper.getrepr(SomeCTypesObject(arg_ctype,
                                                ownsmemory=False))
            args_r.append(r)
        r_result = rtyper.getrepr(SomeCTypesObject(self.restype,
                                                   ownsmemory=True))
        if isinstance(self.ll_type.TO, lltype.ForwardReference):
            FUNCTYPE = get_funcptr_type(args_r, r_result)
            self.ll_type.TO.become(FUNCTYPE)
        self.args_r = args_r
        self.r_result = r_result

    def ctypecheck(self, value):
        return (isinstance(value.__class__, CFuncPtrType) and
                list(value.argtypes) == list(self.argtypes) and
                value.restype == self.restype)

    def initialize_const(self, p, cfuncptr):
        if not cfuncptr:   # passed as arg to functions expecting func pointers
            return
        c, args_r, r_res = get_funcptr_constant(self.rtyper, cfuncptr, None)
        p.c_data[0] = c.value

    def rtype_simple_call(self, hop):
        v_box = hop.inputarg(self, arg=0)
        v_funcptr = self.getvalue(hop.llops, v_box)
        hop2 = hop.copy()
        hop2.r_s_popfirstarg()
        return rtype_funcptr_call(hop2, v_funcptr, self.args_r, self.r_result)


# ____________________________________________________________


def get_funcptr_constant(rtyper, cfuncptr, args_s):
    """Get a Constant ll function pointer from a ctypes function object.
    """
    fnname = cfuncptr.__name__
    args_r, r_res = get_arg_res_repr(rtyper, cfuncptr, args_s)
    FUNCTYPE = get_funcptr_type(args_r, r_res)
    flags = get_funcptr_flags(cfuncptr)
    f = lltype.functionptr(FUNCTYPE, fnname, **flags)
    return inputconst(lltype.typeOf(f), f), args_r, r_res


def get_arg_res_repr(rtyper, cfuncptr, args_s):
    """Get the reprs to use for the arguments and the return value of a
    ctypes function call.  The args_s annotations are used to guess the
    argument types if they are not specified by cfuncptr.argtypes.
    """
    def repr_for_ctype(ctype):
        s = SomeCTypesObject(ctype, ownsmemory=False)
        r = rtyper.getrepr(s)
        return r

    args_r = []
    if getattr(cfuncptr, 'argtypes', None) is not None:
        for ctype in cfuncptr.argtypes:
            args_r.append(repr_for_ctype(ctype))
    else:
        # unspecified argtypes: use ctypes rules for arguments,
        # accepting integers, strings, or None
        for s_arg in args_s:
            if isinstance(s_arg, SomeCTypesObject):
                r_arg = rtyper.getrepr(s_arg)
            elif isinstance(s_arg, annmodel.SomeInteger):
                r_arg = repr_for_ctype(ctypes.c_long)
            elif (isinstance(s_arg, annmodel.SomeString)
                  or s_arg == annmodel.s_None):
                r_arg = repr_for_ctype(ctypes.c_char_p)
            else:
                raise TyperError("call with no argtypes: don't know "
                                 "how to convert argument %r" % (s_arg,))
            args_r.append(r_arg)
    if cfuncptr.restype is not None:
        s_res = SomeCTypesObject(cfuncptr.restype, ownsmemory=True)
        r_res = rtyper.getrepr(s_res)
    else:
        r_res = None
    return args_r, r_res


def get_funcptr_type(args_r, r_res):
    """Get the lltype FUNCTYPE to use for a ctypes function call.
    """
    ARGTYPES = []
    for r_arg in args_r:
        if isinstance(r_arg, CTypesValueRepr):
            # ValueRepr case
            ARGTYPES.append(r_arg.ll_type)
        else:
            # RefRepr case -- i.e. the function argument that we pass by
            # value is e.g. a complete struct
            ARGTYPES.append(r_arg.c_data_type)
    if r_res is not None:
        RESTYPE = r_res.ll_type
    else:
        RESTYPE = lltype.Void
    return lltype.FuncType(ARGTYPES, RESTYPE)


def get_funcptr_flags(cfuncptr):
    """Get the fnptr flags to use for the given concrete ctypes function.
    """
    kwds = {'external': 'C'}
    if hasattr(cfuncptr, 'llinterp_friendly_version'):
        kwds['_callable'] = cfuncptr.llinterp_friendly_version
    suppress_pyerr_occurred = False
    if (cfuncptr._flags_ & ctypes._FUNCFLAG_PYTHONAPI) == 0:
        suppress_pyerr_occurred = True
    if hasattr(cfuncptr, '_rctypes_pyerrchecker_'):
        suppress_pyerr_occurred = True
    if suppress_pyerr_occurred:
        kwds['includes'] = getattr(cfuncptr, 'includes', ())
        kwds['libraries'] = getattr(cfuncptr, 'libraries', ())
    #else:
    #   no 'includes': hack to trigger in GenC a PyErr_Occurred() check
    return kwds


def rtype_funcptr_call(hop, v_funcptr, args_r, r_res, pyerrchecker=None):
    """Generate a call to the given ll function pointer.
    """
    hop.rtyper.call_all_setups()
    vlist = hop.inputargs(*args_r)
    unwrapped_args_v = []
    for r_arg, v in zip(args_r, vlist):
        if isinstance(r_arg, CTypesValueRepr):
            # ValueRepr case
            unwrapped_args_v.append(r_arg.getvalue(hop.llops, v))
        elif isinstance(r_arg, CTypesRefRepr):
            # RefRepr case -- i.e. the function argument that we pass by
            # value is e.g. a complete struct; we pass a pointer to it
            # in the low-level graphs and it's up to the back-end to
            # generate the correct dereferencing
            unwrapped_args_v.append(r_arg.get_c_data(hop.llops, v))
        else:
            assert 0, "ctypes func call got a non-ctypes arg repr"

    FUNCTYPE = v_funcptr.concretetype.TO
    hop.exception_cannot_occur()
    if isinstance(v_funcptr, Constant):
        opname = 'direct_call'
    else:
        unwrapped_args_v.append(inputconst(lltype.Void, None))
        opname = 'indirect_call'
    v_result = hop.genop(opname, [v_funcptr]+unwrapped_args_v,
                         resulttype = FUNCTYPE.RESULT)

    if pyerrchecker is not None:
        # special extension to support the CPyObjSpace
        # XXX hackish: someone else -- like the annotator policy --
        # must ensure that this extra function has been annotated
        from pypy.translator.translator import graphof
        graph = graphof(hop.rtyper.annotator.translator, pyerrchecker)
        hop.llops.record_extra_call(graph)
        # build the 'direct_call' operation
        f = hop.rtyper.getcallable(graph)
        c = hop.inputconst(lltype.typeOf(f), f)
        hop.genop('direct_call', [c])

    if r_res is not None:
        v_result = r_res.return_value(hop.llops, v_result)
    return v_result
