from pypy.objspace.flow.model import Variable, Constant
from pypy.objspace.flow.model import Block, Link, FunctionGraph, checkgraph
from pypy.rpython.lltypesystem.lltype import \
     Ptr, PyObject, typeOf, Signed, FuncType, functionptr
from pypy.rpython.rtyper import LowLevelOpList
from pypy.rpython.rmodel import inputconst, PyObjPtr
from pypy.rpython.robject import pyobj_repr
from pypy.interpreter.pycode import CO_VARARGS

from pypy.rpython.typesystem import getfunctionptr


def gen_wrapper(func, translator):
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

    if translator.annotator is None:
        # get the graph from the translator, "push it back" so that it's
        # still available for further buildflowgraph() calls
        graph = translator.buildflowgraph(func)
        translator._prebuilt_graphs[func] = graph
    else:
        bk = translator.annotator.bookkeeper
        graph = bk.getdesc(func).cachedgraph(None)

    f = getfunctionptr(graph)
    FUNCTYPE = typeOf(f).TO
    assert len(FUNCTYPE.ARGS) == nb_positional_args + vararg

    newops = LowLevelOpList(translator.rtyper)

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
        v.set_name('a', i)
        varguments.append(v)

    if vararg:
        # "vararg = vargs[n:]"
        vlist = [vargs,
                 Constant(nb_positional_args),
                 Constant(None),
                 ]
        vararg = newops.genop('getslice', vlist, resulttype=Ptr(PyObject))
        vararg.set_name('vararg', 0)
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
        if FUNCTYPE.ARGS[i] != PyObjPtr:
            # "argument_i = type_conversion_operations(argument_i)"
            rtyper = translator.rtyper
            assert rtyper is not None, (
                "needs the rtyper to perform argument conversions")
            r_arg = rtyper.bindingrepr(inputargs[i])
            varguments[i] = newops.convertvar(varguments[i],
                                              r_from = pyobj_repr,
                                                r_to = r_arg)

    # "result = direct_call(func, argument_0, argument_1, ..)"
    vlist = [inputconst(typeOf(f), f)] + varguments
    vresult = newops.genop('direct_call', vlist, resulttype=FUNCTYPE.RESULT)

    if FUNCTYPE.RESULT != PyObjPtr:
        # convert "result" back to a PyObject
        rtyper = translator.rtyper
        assert rtyper is not None, (
            "needs the rtyper to perform function result conversions")
        r_result = rtyper.bindingrepr(f._obj.graph.getreturnvar())
        vresult = newops.convertvar(vresult,
                                    r_from = r_result,
                                      r_to = pyobj_repr)

    # "return result"
    block = Block([vself, vargs, vkwds])
    wgraph = FunctionGraph('pyfn_' + func.func_name, block)
    translator.update_call_graph(wgraph, graph, object())
    translator.graphs.append(wgraph)
    block.operations[:] = newops
    block.closeblock(Link([vresult], wgraph.returnblock))
    checkgraph(wgraph)

    if translator.rtyper is not None:
        # the above convertvar()s may have created and annotated new helpers
        # that need to be specialized now
        translator.rtyper.specialize_more_blocks()

    return functionptr(FuncType([PyObjPtr,
                                 PyObjPtr,
                                 PyObjPtr],
                                PyObjPtr),
                       wgraph.name,
                       graph = wgraph,
                       exception_policy = "CPython")
