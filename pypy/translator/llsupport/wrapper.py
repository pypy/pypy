from pypy.objspace.flow.model import Variable
from pypy.objspace.flow.model import Block, Link, FunctionGraph, checkgraph
from pypy.rpython.lltypesystem.lltype import \
     Ptr, PyObject, typeOf, Signed, FuncType, functionptr, nullptr, Void
from pypy.rpython.rtyper import LowLevelOpList
from pypy.rpython.rmodel import inputconst, PyObjPtr
from pypy.rpython.robject import pyobj_repr

from pypy.rpython.typesystem import getfunctionptr



def new_wrapper(func, translator, newname=None):
    # The basic idea is to produce a flow graph from scratch, using the
    # help of the rtyper for the conversion of the arguments after they
    # have been decoded.
    
    bk = translator.annotator.bookkeeper
    graph = bk.getdesc(func).getuniquegraph()

    f = getfunctionptr(graph)
    FUNCTYPE = typeOf(f).TO

    newops = LowLevelOpList(translator.rtyper)

    varguments = []
    for var in graph.startblock.inputargs:
        v = Variable(var)
        v.concretetype = PyObjPtr
        varguments.append(v)

    wrapper_inputargs = varguments[:]
    # use the rtyper to produce the conversions
    inputargs = f._obj.graph.getargs()
    for i in range(len(varguments)):
        if FUNCTYPE.ARGS[i] != PyObjPtr:
            rtyper = translator.rtyper
            r_arg = rtyper.bindingrepr(inputargs[i])
            # give the rtyper a chance to know which function we are wrapping
            rtyper.set_wrapper_context(func)
            varguments[i] = newops.convertvar(varguments[i],
                                              r_from = pyobj_repr,
                                              r_to = r_arg)
            rtyper.set_wrapper_context(None)

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
    block = Block(wrapper_inputargs)
    wgraph = FunctionGraph('pyfn_' + (newname or func.func_name), block)
    translator.update_call_graph(wgraph, graph, object())
    translator.graphs.append(wgraph)
    block.operations[:] = newops
    block.closeblock(Link([vresult], wgraph.returnblock))
    wgraph.getreturnvar().concretetype = PyObjPtr
    checkgraph(wgraph)

    # the above convertvar()s may have created and annotated new helpers
    # that need to be specialized now
    translator.rtyper.specialize_more_blocks()

    return functionptr(FuncType([PyObjPtr] * len(wrapper_inputargs),
                                PyObjPtr),
                       wgraph.name,
                       graph = wgraph,
                       exception_policy = "CPython")

