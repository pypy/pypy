"""
Functions that generate flow graphs and operations.
The functions below produce L2 graphs, but they define an interface
that can be used to produce any other kind of graph.
"""

from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.objspace.flow import model as flowmodel
from pypy.translator.simplify import eliminate_empty_blocks, join_blocks
from pypy.rpython.module.support import init_opaque_object
from pypy.rpython.module.support import to_opaque_object, from_opaque_object
from pypy.rpython.module.support import from_rstr
from pypy.jit.codegen.llvm.jitcode import JITcode


# for debugging, sanity checks in non-RPython code
reveal = from_opaque_object

def initblock(opaqueptr):
    init_opaque_object(opaqueptr, flowmodel.Block([]))

def newblock():
    blockcontainer = lltype.malloc(BLOCKCONTAINERTYPE)
    initblock(blockcontainer.obj)
    return blockcontainer

def geninputarg(blockcontainer, gv_CONCRETE_TYPE):
    block = from_opaque_object(blockcontainer.obj)
    CONCRETE_TYPE = from_opaque_object(gv_CONCRETE_TYPE).value
    v = flowmodel.Variable()
    v.concretetype = CONCRETE_TYPE
    block.inputargs.append(v)
    return to_opaque_object(v)

def _inputvars(vars):
    if not isinstance(vars, list):
        n = vars.ll_length()
        vars = vars.ll_items()        
    else:
        n = len(vars)
    res = []
    for i in range(n):
        v = from_opaque_object(vars[i])
        assert isinstance(v, (flowmodel.Constant, flowmodel.Variable))
        res.append(v)
    return res

# is opname a runtime value?
def genop(blockcontainer, opname, vars, gv_RESULT_TYPE):
    if not isinstance(opname, str):
        opname = from_rstr(opname)
    block = from_opaque_object(blockcontainer.obj)
    RESULT_TYPE = from_opaque_object(gv_RESULT_TYPE).value
    opvars = _inputvars(vars)    
    v = flowmodel.Variable()
    v.concretetype = RESULT_TYPE
    op = flowmodel.SpaceOperation(opname, opvars, v)
    block.operations.append(op)
    return to_opaque_object(v)

def gencallableconst(blockcontainer, name, targetcontainer, gv_FUNCTYPE):
    # is name useful, is it runtime variable?
    target = from_opaque_object(targetcontainer.obj)
    FUNCTYPE = from_opaque_object(gv_FUNCTYPE).value
    fptr = lltype.functionptr(FUNCTYPE, name,
                              graph=_buildgraph(target))
    return genconst(fptr)

def genconst(llvalue):
    v = flowmodel.Constant(llvalue)
    v.concretetype = lltype.typeOf(llvalue)
    if v.concretetype == lltype.Void: # XXX genconst should not really be used for Void constants
        assert not isinstance(llvalue, str) and not isinstance(llvalue, lltype.LowLevelType)
    return to_opaque_object(v)

def revealconst(T, gv_value):
    c = from_opaque_object(gv_value)
    assert isinstance(c, flowmodel.Constant)
    if isinstance(T, lltype.Ptr):
        return lltype.cast_pointer(T, c.value)
    elif T == llmemory.Address:
        return llmemory.cast_ptr_to_adr(c.value)
    else:
        return lltype.cast_primitive(T, c.value)
                                    
# XXX
# temporary interface; it's unclera if genop itself should change to ease dinstinguishing
# Void special args from the rest. Or there should be variation for the ops involving them

def placeholder(dummy):
    c = flowmodel.Constant(dummy)
    c.concretetype = lltype.Void
    return to_opaque_object(c)    

def constFieldName(name):
    assert isinstance(name, str)
    c = flowmodel.Constant(name)
    c.concretetype = lltype.Void
    return to_opaque_object(c)

def constTYPE(TYPE):
    assert isinstance(TYPE, lltype.LowLevelType)
    c = flowmodel.Constant(TYPE)
    c.concretetype = lltype.Void
    return to_opaque_object(c)

def closeblock1(blockcontainer):
    block = from_opaque_object(blockcontainer.obj)
    link = flowmodel.Link([], None)
    block.closeblock(link)
    return to_opaque_object(link)

def closeblock2into(blockcontainer, exitswitch, linkpair):
    block = from_opaque_object(blockcontainer.obj)
    exitswitch = from_opaque_object(exitswitch)
    assert isinstance(exitswitch, flowmodel.Variable)
    block.exitswitch = exitswitch
    false_link = flowmodel.Link([], None)
    false_link.exitcase = False
    false_link.llexitcase = False
    true_link = flowmodel.Link([], None)
    true_link.exitcase = True
    true_link.llexitcase = True
    block.closeblock(false_link, true_link)
    linkpair.item0 = to_opaque_object(false_link)
    linkpair.item1 = to_opaque_object(true_link)

def closeblock2(blockcontainer, exitswitch):
    linkpair = lltype.malloc(LINKPAIR)
    closeblock2into(blockcontainer, exitswitch, linkpair) 
    return linkpair

def _closelink(link, vars, targetblock):
    if isinstance(link, flowmodel.Link):
        for v in vars:
            assert isinstance(v, (flowmodel.Variable, flowmodel.Constant))
        assert ([v.concretetype for v in vars] ==
                [v.concretetype for v in targetblock.inputargs])
        link.args[:] = vars
        link.target = targetblock
    elif isinstance(link, flowmodel.FunctionGraph):
        graph = link
        graph.startblock = targetblock
        targetblock.isstartblock = True
    else:
        raise TypeError

def closelink(link, vars, targetblockcontainer):
    link = from_opaque_object(link)
    targetblock = from_opaque_object(targetblockcontainer.obj)
    vars = _inputvars(vars)
    return _closelink(link, vars, targetblock) 

def closereturnlink(link, returnvar):
    returnvar = from_opaque_object(returnvar)
    link = from_opaque_object(link)
    v = flowmodel.Variable()
    v.concretetype = returnvar.concretetype
    pseudoreturnblock = flowmodel.Block([v])
    pseudoreturnblock.operations = ()
    _closelink(link, [returnvar], pseudoreturnblock)

def _patchgraph(graph):
    returntype = None
    for link in graph.iterlinks():
        if link.target.operations == ():
            assert len(link.args) == 1    # for now
            if returntype is None:
                returntype = link.target.inputargs[0].concretetype
            else:
                assert returntype == link.target.inputargs[0].concretetype
            link.target = graph.returnblock
    if returntype is None:
        returntype = lltype.Void
    graph.returnblock.inputargs[0].concretetype = returntype

class PseudoRTyper(object):
    def __init__(self):
        from pypy.rpython.typesystem import LowLevelTypeSystem
        self.type_system = LowLevelTypeSystem.instance

def _buildgraph(block):
    graph = flowmodel.FunctionGraph('generated', block)
    _patchgraph(graph)
    flowmodel.checkgraph(graph)
    eliminate_empty_blocks(graph)
    join_blocks(graph)
    graph.rgenop = True
    return graph

def buildgraph(blockcontainer):
    block = from_opaque_object(blockcontainer.obj)
    return _buildgraph(block)

def testgengraph(gengraph, args, viewbefore=False):
    from pypy.rpython.llinterp import LLInterpreter
    if viewbefore:
        gengraph.show()
    #llinterp = LLInterpreter(PseudoRTyper())
    #return llinterp.eval_graph(gengraph, args)
    jitcode = JITcode(PseudoRTyper())
    return jitcode.eval_graph(gengraph, args)
    
def runblock(blockcontainer, args, viewbefore=False):
    graph = buildgraph(blockcontainer)
    return testgengraph(graph, args, viewbefore)

# ____________________________________________________________
# RTyping of the above functions

from pypy.rpython.extfunctable import declaretype, declareptrtype, declare

blocktypeinfo = declaretype(flowmodel.Block, "Block")
consttypeinfo = declareptrtype(flowmodel.Constant, "ConstOrVar")
vartypeinfo   = declareptrtype(flowmodel.Variable, "ConstOrVar")
vartypeinfo.set_lltype(consttypeinfo.get_lltype())   # force same lltype
linktypeinfo  = declareptrtype(flowmodel.Link, "Link")

CONSTORVAR = lltype.Ptr(consttypeinfo.get_lltype())
BLOCKCONTAINERTYPE = blocktypeinfo.get_lltype()
BLOCK = lltype.Ptr(BLOCKCONTAINERTYPE)
LINK = lltype.Ptr(linktypeinfo.get_lltype())

fieldnames = ['item%d' % i for i in range(2)]
lltypes = [LINK]*2
fields = tuple(zip(fieldnames, lltypes))    
LINKPAIR = lltype.GcStruct('tuple2', *fields)

# helpers
def setannotation(func, TYPE):
    func.compute_result_annotation = lambda *args_s: TYPE 

def setspecialize(func):
    # for now
    def specialize_as_direct_call(hop):
        FUNCTYPE = lltype.FuncType([r.lowleveltype for r in hop.args_r], hop.r_result.lowleveltype)
        args_v = hop.inputargs(*hop.args_r)
        funcptr = lltype.functionptr(FUNCTYPE, func.__name__, _callable=func)
        cfunc = hop.inputconst(lltype.Ptr(FUNCTYPE), funcptr)
        return hop.genop('direct_call', [cfunc] + args_v, hop.r_result)
    func.specialize = specialize_as_direct_call

# annotations
from pypy.annotation import model as annmodel

s_ConstOrVar = annmodel.SomePtr(CONSTORVAR)#annmodel.SomeExternalObject(flowmodel.Variable)
s_Link = annmodel.SomePtr(LINK)#annmodel.SomeExternalObject(flowmodel.Link)
s_LinkPair = annmodel.SomePtr(lltype.Ptr(LINKPAIR))

setannotation(initblock, None)
setannotation(geninputarg, s_ConstOrVar)
setannotation(genop, s_ConstOrVar)
setannotation(genconst, s_ConstOrVar)
revealconst.compute_result_annotation = lambda s_T, s_gv: annmodel.lltype_to_annotation(s_T.const)
setannotation(closeblock1, s_Link)
setannotation(closeblock2, s_LinkPair)
setannotation(closelink, None)
setannotation(closereturnlink, None)

# specialize
setspecialize(initblock)
setspecialize(geninputarg)
setspecialize(genop)
setspecialize(genconst)
setspecialize(revealconst)
setspecialize(closeblock1)
setspecialize(closeblock2)
setspecialize(closelink)
setspecialize(closereturnlink)

# XXX(for now) void constant constructors
setannotation(constFieldName, s_ConstOrVar)
setannotation(constTYPE, s_ConstOrVar)
setannotation(placeholder, s_ConstOrVar)

def set_specialize_void_constant_constructor(func):
    # for now
    def specialize_as_constant(hop):
        llvalue = func(hop.args_s[0].const)
        return hop.inputconst(lltype.typeOf(llvalue), llvalue)
    func.specialize = specialize_as_constant

set_specialize_void_constant_constructor(placeholder)
set_specialize_void_constant_constructor(constFieldName)
set_specialize_void_constant_constructor(constTYPE)
