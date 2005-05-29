from pypy.objspace.flow.model import Variable, Constant, SpaceOperation
from pypy.objspace.flow.model import Block, Link, FunctionGraph, checkgraph
from pypy.annotation import model as annmodel
from pypy.rpython.lltype import GcPtr, NonGcPtr, PyObject, typeOf, Signed, Void
from pypy.rpython.lltype import FuncType, functionptr
from pypy.rpython.rtyper import LowLevelOpList, inputconst
from pypy.interpreter.pycode import CO_VARARGS


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
    vself.concretetype = NonGcPtr(PyObject)
    vargs.concretetype = NonGcPtr(PyObject)
    vkwds.concretetype = NonGcPtr(PyObject)

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

        v = newops.genop(opname, vlist, resulttype=GcPtr(PyObject))
        v._name = 'a%d' % i
        varguments.append(v)

    if vararg:
        # "vararg = vargs[n:]"
        vlist = [vargs,
                 Constant(nb_positional_args),
                 Constant(None),
                 ]
        vararg = newops.genop('getslice', vlist, resulttype=GcPtr(PyObject))
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
        s_arg = rtyper.annotator.binding(inputargs[i], True)
        if s_arg is not None:
            varguments[i] = newops.convertvar(varguments[i],
                                              s_from = annmodel.SomeObject(),
                                                s_to = s_arg)

    # "result = direct_call(func, argument_0, argument_1, ..)"
    vlist = [inputconst(typeOf(f), f)] + varguments
    vresult = newops.genop('direct_call', vlist, resulttype=FUNCTYPE.RESULT)

    # convert "result" back to a PyObject
    s_result = rtyper.annotator.binding(f._obj.graph.getreturnvar(), True)
    if s_result is not None:
        vresult = newops.convertvar(vresult,
                                    s_from = s_result,
                                      s_to = annmodel.SomeObject())

    # "return result"
    block = Block([vself, vargs, vkwds])
    wgraph = FunctionGraph('pyfn_' + func.func_name, block)
    block.operations[:] = newops
    block.closeblock(Link([vresult], wgraph.returnblock))
    checkgraph(wgraph)

    return functionptr(FuncType([NonGcPtr(PyObject),
                                 NonGcPtr(PyObject),
                                 NonGcPtr(PyObject)],
                                GcPtr(PyObject)),
                       wgraph.name,
                       graph = wgraph)
