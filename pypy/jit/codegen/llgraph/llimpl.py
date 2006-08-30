"""
Functions that generate flow graphs and operations.
The functions below produce L2 graphs, but they define an interface
that can be used to produce any other kind of graph.
"""

from pypy.rpython.lltypesystem import lltype, llmemory, rtupletype
from pypy.objspace.flow import model as flowmodel
from pypy.translator.simplify import eliminate_empty_blocks, join_blocks
from pypy.rpython.module.support import init_opaque_object
from pypy.rpython.module.support import to_opaque_object, from_opaque_object
from pypy.rpython.module.support import LLSupport
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.lltypesystem.rclass import fishllattr


# for debugging, sanity checks in non-RPython code
reveal = from_opaque_object

def isptrtype(gv_type):
    c = from_opaque_object(gv_type)
    return isinstance(c.value, lltype.Ptr)

def initblock(opaqueptr):
    init_opaque_object(opaqueptr, flowmodel.Block([]))

def newblock():
    blockcontainer = lltype.malloc(BLOCKCONTAINERTYPE)
    initblock(blockcontainer.obj)
    return blockcontainer

def geninputarg(blockcontainer, gv_CONCRETE_TYPE):
    block = from_opaque_object(blockcontainer.obj)
    assert not block.operations, "block already contains operations"
    assert block.exits == [], "block already closed"
    CONCRETE_TYPE = from_opaque_object(gv_CONCRETE_TYPE).value
    v = flowmodel.Variable()
    v.concretetype = CONCRETE_TYPE
    block.inputargs.append(v)
    return to_opaque_object(v)

def _inputvars(vars):
    newvars = []
    if not isinstance(vars, list):
        n = vars.ll_length()
        vars = vars.ll_items()
        for i in range(n):
            v = vars[i]
            if not v:
                v = dummy_placeholder
            else:
                v = fishllattr(v, 'v', v)
            newvars.append(v)
    else:
        for v in vars:
            if not v:
                v = dummy_placeholder
            else:
                v = getattr(v, 'v', v)
            newvars.append(v)
    res = []
    for v1 in newvars:
        v = from_opaque_object(v1)
        assert isinstance(v, (flowmodel.Constant, flowmodel.Variable))
        res.append(v)
    return res

def genop(blockcontainer, opname, vars_gv, gv_RESULT_TYPE):
    # 'opname' is a constant string
    # gv_RESULT_TYPE comes from constTYPE
    if not isinstance(opname, str):
        opname = LLSupport.from_rstr(opname)
    block = from_opaque_object(blockcontainer.obj)
    assert block.exits == [], "block already closed"
    if isinstance(gv_RESULT_TYPE, lltype.LowLevelType):
        RESULT_TYPE = gv_RESULT_TYPE
    else:
        RESULT_TYPE = from_opaque_object(gv_RESULT_TYPE).value
    opvars = _inputvars(vars_gv)
    v = flowmodel.Variable()
    v.concretetype = RESULT_TYPE
    op = flowmodel.SpaceOperation(opname, opvars, v)
    block.operations.append(op)
    return to_opaque_object(v)

def gencallableconst(name, targetcontainer, gv_FUNCTYPE):
    # 'name' is just a way to track things
    if not isinstance(name, str):
        name = LLSupport.from_rstr(name)
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

def isconst(gv_value):
    c = from_opaque_object(gv_value)
    return isinstance(c, flowmodel.Constant)

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

def closeblock2(blockcontainer, exitswitch):
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
    return pseudotuple(to_opaque_object(false_link),
                       to_opaque_object(true_link))

class pseudotuple(object):
    # something that looks both like a hl and a ll tuple
    def __init__(self, *items):
        self._TYPE = rtupletype.TUPLE_TYPE(
            [lltype.typeOf(item) for item in items])
        for i, item in enumerate(items):
            setattr(self, 'item%d' % i, item)
        self._items = items
    def __iter__(self):
        return iter(self._items)

def _closelink(link, vars, targetblock):
    if isinstance(link, flowmodel.Link):
        blockvars = dict.fromkeys(link.prevblock.getvariables())
        for v in vars:
            if isinstance(v, flowmodel.Variable):
                assert v in blockvars    # link using vars not from prevblock!
            else:
                assert isinstance(v, flowmodel.Constant)
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
    _closelink(link, vars, targetblock)

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

def testgengraph(gengraph, args, viewbefore=False, executor=LLInterpreter):
    if viewbefore:
        gengraph.show()
    llinterp = executor(PseudoRTyper())
    return llinterp.eval_graph(gengraph, args)
    
def runblock(blockcontainer, args, viewbefore=False, executor=LLInterpreter):
    graph = buildgraph(blockcontainer)
    return testgengraph(graph, args, viewbefore, executor)

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

# support constants and types

nullvar = lltype.nullptr(CONSTORVAR.TO)
nullblock = lltype.nullptr(BLOCK.TO)
nulllink = lltype.nullptr(LINK.TO)
gv_Void = constTYPE(lltype.Void)

dummy_placeholder = placeholder("dummy")


# helpers
def setannotation(func, annotation, specialize_as_constant=False):

    class Entry(ExtRegistryEntry):
        "Annotation and specialization for calls to 'func'."
        _about_ = func

        if annotation is None or isinstance(annotation, annmodel.SomeObject):
            s_result_annotation = annotation
        else:
            def compute_result_annotation(self, *args_s):
                return annotation(*args_s)

        if specialize_as_constant:
            def specialize_call(self, hop):
                llvalue = func(hop.args_s[0].const)
                return hop.inputconst(lltype.typeOf(llvalue), llvalue)
        else:
            # specialize as direct_call
            def specialize_call(self, hop):
                FUNCTYPE = lltype.FuncType([r.lowleveltype for r in hop.args_r],
                                           hop.r_result.lowleveltype)
                args_v = hop.inputargs(*hop.args_r)
                funcptr = lltype.functionptr(FUNCTYPE, func.__name__,
                                             _callable=func)
                cfunc = hop.inputconst(lltype.Ptr(FUNCTYPE), funcptr)
                return hop.genop('direct_call', [cfunc] + args_v, hop.r_result)

# annotations
from pypy.annotation import model as annmodel

s_ConstOrVar = annmodel.SomePtr(CONSTORVAR)#annmodel.SomeExternalObject(flowmodel.Variable)
s_Link = annmodel.SomePtr(LINK)#annmodel.SomeExternalObject(flowmodel.Link)
s_LinkPair = annmodel.SomeTuple([s_Link, s_Link])

setannotation(initblock, None)
setannotation(geninputarg, s_ConstOrVar)
setannotation(genop, s_ConstOrVar)
setannotation(gencallableconst, s_ConstOrVar)
setannotation(genconst, s_ConstOrVar)
setannotation(revealconst, lambda s_T, s_gv: annmodel.lltype_to_annotation(
                                                  s_T.const))
setannotation(isconst, annmodel.SomeBool())
setannotation(closeblock1, s_Link)
setannotation(closeblock2, s_LinkPair)
setannotation(closelink, None)
setannotation(closereturnlink, None)

setannotation(isptrtype, annmodel.SomeBool())

# XXX(for now) void constant constructors
setannotation(constFieldName, s_ConstOrVar, specialize_as_constant=True)
setannotation(constTYPE,      s_ConstOrVar, specialize_as_constant=True)
setannotation(placeholder,    s_ConstOrVar, specialize_as_constant=True)
