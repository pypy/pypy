from pypy.objspace.flow.model import Variable, Constant, SpaceOperation
from pypy.objspace.flow.model import Block, Link, FunctionGraph, checkgraph
from pypy.annotation import model as annmodel
from pypy.rpython.lltype import Ptr, PyObject, typeOf, Signed, Void
from pypy.rpython.lltype import FuncType, functionptr
from pypy.rpython.rtyper import LowLevelOpList, inputconst
from pypy.rpython.robject import pyobj_repr
from pypy.interpreter.pycode import CO_VARARGS


PyObjPtr = Ptr(PyObject)

def gen_wrapper(func, rtyper):
    """generate a wrapper function for 'func' that can be put in a
    PyCFunction object.  The wrapper has signature

        PyObject *pyfn_xxx(PyObject *self, PyObject *args, PyObject* kw);
    """
    # The basic idea is to produce a flow graph from scratch, using the
    # help of the rtyper for the conversion of the arguments after they
    # have been decoded.
    
    # get the fully typed low-level pointer to the function, if available
    nb_positional_args = func.func_code.co_argcount
    vararg = bool(func.func_code.co_flags & CO_VARARGS)
    f = rtyper.getfunctionptr(func)
    FUNCTYPE = typeOf(f).TO
    assert len(FUNCTYPE.ARGS) == nb_positional_args + vararg

    newops = LowLevelOpList(rtyper)

    # "def wrapper(self, args, kwds)"
    vself = Variable('self')
    vargs = Variable('args')
    vkwds = Variable('kwds')
    vfname = Constant(func.func_name)
    # avoid incref/decref on the arguments: 'self' and 'kwds' can be NULL
    vself.concretetype = PyObjPtr
    vargs.concretetype = PyObjPtr
    vkwds.concretetype = PyObjPtr

    varguments = []
    varnames = func.func_code.co_varnames
    func_defaults = func.func_defaults or ()
    for i in range(nb_positional_args):
        # "argument_i = decode_arg(fname, i, name, vargs, vkwds)"  or
        # "argument_i = decode_arg_def(fname, i, name, vargs, vkwds, default)"
        vlist = [vfname,
                 inputconst(Signed, i),
                 Constant(varnames[i]),
                 vargs,
                 vkwds]
        try:
            default_value = func_defaults[i - nb_positional_args]
        except IndexError:
            opname = 'decode_arg'
        else:
            opname = 'decode_arg_def'
            vlist.append(Constant(default_value))

        v = newops.genop(opname, vlist, resulttype=Ptr(PyObject))
        v._name = 'a%d' % i
        varguments.append(v)

    if vararg:
        # "vararg = vargs[n:]"
        vlist = [vargs,
                 Constant(nb_positional_args),
                 Constant(None),
                 ]
        vararg = newops.genop('getslice', vlist, resulttype=Ptr(PyObject))
        vararg._name = 'vararg'
        varguments.append(vararg)
    else:
        # "check_no_more_arg(fname, n, vargs)"
        vlist = [vfname,
                 inputconst(Signed, nb_positional_args),
                 vargs,
                 ]
        newops.genop('check_no_more_arg', vlist)

    # use the rtyper to produce the conversions
    inputargs = f._obj.graph.getargs()
    for i in range(len(varguments)):
        # "argument_i = type_conversion_operations(argument_i)"
        r_arg = rtyper.bindingrepr(inputargs[i])
        varguments[i] = newops.convertvar(varguments[i],
                                          r_from = pyobj_repr,
                                            r_to = r_arg)

    # "result = direct_call(func, argument_0, argument_1, ..)"
    vlist = [inputconst(typeOf(f), f)] + varguments
    vresult = newops.genop('direct_call', vlist, resulttype=FUNCTYPE.RESULT)

    # convert "result" back to a PyObject
    r_result = rtyper.bindingrepr(f._obj.graph.getreturnvar())
    vresult = newops.convertvar(vresult,
                                r_from = r_result,
                                  r_to = pyobj_repr)

    # "return result"
    block = Block([vself, vargs, vkwds])
    wgraph = FunctionGraph('pyfn_' + func.func_name, block)
    block.operations[:] = newops
    block.closeblock(Link([vresult], wgraph.returnblock))
    checkgraph(wgraph)

    return functionptr(FuncType([PyObjPtr,
                                 PyObjPtr,
                                 PyObjPtr],
                                PyObjPtr),
                       wgraph.name,
                       graph = wgraph)
