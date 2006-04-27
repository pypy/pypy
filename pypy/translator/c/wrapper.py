from pypy.objspace.flow.model import Variable, Constant
from pypy.objspace.flow.model import Block, Link, FunctionGraph, checkgraph
from pypy.rpython.lltypesystem.lltype import \
     Ptr, PyObject, typeOf, Signed, FuncType, functionptr, nullptr, Void
from pypy.rpython.rtyper import LowLevelOpList
from pypy.rpython.rmodel import inputconst, PyObjPtr
from pypy.rpython.robject import pyobj_repr
from pypy.interpreter.pycode import CO_VARARGS

from pypy.rpython.typesystem import getfunctionptr
from pypy.annotation.model import s_None, SomeInstance
from pypy.translator.backendopt.inline import simple_inline_function

ALWAYS_INLINE = False

def gen_wrapper(func, translator, newname=None, as_method=False):
    """generate a wrapper function for 'func' that can be put in a
    PyCFunction object.  The wrapper has signature

        PyObject *pyfn_xxx(PyObject *self, PyObject *args, PyObject* kw);
    """
    # The basic idea is to produce a flow graph from scratch, using the
    # help of the rtyper for the conversion of the arguments after they
    # have been decoded.
    
    # get the fully typed low-level pointer to the function, if available

    do_inline = ALWAYS_INLINE
    if translator.annotator is None:
        # get the graph from the translator, "push it back" so that it's
        # still available for further buildflowgraph() calls
        graph = translator.buildflowgraph(func)
        translator._prebuilt_graphs[func] = graph
    else:
        if isinstance(func, FunctionGraph):
            graph = func
            func = graph.func
            # in this case we want to inline for sure, because we
            # created this extra graph with a single call-site.
            do_inline = True
        else:
            bk = translator.annotator.bookkeeper
            graph = bk.getdesc(func).cachedgraph(None)

    f = getfunctionptr(graph)
    FUNCTYPE = typeOf(f).TO
    nb_positional_args = func.func_code.co_argcount
    vararg = bool(func.func_code.co_flags & CO_VARARGS)
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
    if as_method:
        nb_positional_args -= 1
        varnames = varnames[1:]
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
        #v.set_name('a', i)
        varguments.append(v)

    if vararg:
        # "vararg = vargs[n:]"
        vlist = [vargs,
                 Constant(nb_positional_args),
                 Constant(None),
                 ]
        vararg = newops.genop('getslice', vlist, resulttype=Ptr(PyObject))
        #vararg.set_name('vararg', 0)
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
    if as_method:
        varguments.insert(0, vself)
    for i in range(len(varguments)):
        if FUNCTYPE.ARGS[i] != PyObjPtr:
            # "argument_i = type_conversion_operations(argument_i)"
            rtyper = translator.rtyper
            assert rtyper is not None, (
                "needs the rtyper to perform argument conversions")
            r_arg = rtyper.bindingrepr(inputargs[i])
            # give the rtyper a chance to know which function we are wrapping
            rtyper.set_wrapper_context(func)
            varguments[i] = newops.convertvar(varguments[i],
                                              r_from = pyobj_repr,
                                                r_to = r_arg)
            rtyper.set_wrapper_context(None)

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
    wgraph = FunctionGraph('pyfn_' + (newname or func.func_name), block)
    translator.update_call_graph(wgraph, graph, object())
    translator.graphs.append(wgraph)
    block.operations[:] = newops
    block.closeblock(Link([vresult], wgraph.returnblock))
    checkgraph(wgraph)

    if translator.rtyper is not None:
        # the above convertvar()s may have created and annotated new helpers
        # that need to be specialized now
        translator.rtyper.specialize_more_blocks()

    if do_inline:
        simple_inline_function(translator, graph, wgraph)
    return functionptr(FuncType([PyObjPtr,
                                 PyObjPtr,
                                 PyObjPtr],
                                PyObjPtr),
                       wgraph.name,
                       graph = wgraph,
                       exception_policy = "CPython")

def new_method_graph(graph, clsdef, newname, translator):
    ann = translator.annotator
    rtyper = translator.rtyper

    f = getfunctionptr(graph)
    FUNCTYPE = typeOf(f).TO

    newops = LowLevelOpList(translator.rtyper)

    callargs = graph.getargs()[:]
    v_self_old = callargs.pop(0)
    v_self = Variable(v_self_old.name)
    binding = SomeInstance(clsdef)
    v_self.concretetype = rtyper.getrepr(binding).lowleveltype
    ann.setbinding(v_self, binding)
    v_self_call = newops.convertvar(v_self,
                                  r_from = rtyper.bindingrepr(v_self),
                                    r_to = rtyper.bindingrepr(v_self_old))

    vlist = [inputconst(typeOf(f), f)] + [v_self_call] + callargs
    newops.genop('direct_call', vlist, resulttype=Void)

    # "return result"
    funcargs = [v_self] + callargs
    block = Block(funcargs)
    newgraph = FunctionGraph(newname, block)
    translator.update_call_graph(newgraph, graph, object())
    translator.graphs.append(newgraph)
    block.operations[:] = newops
    block.closeblock(Link([inputconst(Void, None)], newgraph.returnblock))

    vres = newgraph.getreturnvar()
    ann.setbinding(vres, s_None)
    checkgraph(newgraph)
    # pretend to be the same function, as we actually
    # will become inlined.
    newgraph.func = graph.func
    translator.rtyper.specialize_more_blocks()
    # not sure if we want this all the time?
    if ALWAYS_INLINE:
        simple_inline_function(translator, graph, newgraph)
    return newgraph
