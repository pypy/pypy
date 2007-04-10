"""
Functions that generate flow graphs and operations.
The functions below produce L2 graphs, but they define an interface
that can be used to produce any other kind of graph.
"""

from pypy.rpython.lltypesystem import lltype, llmemory, rtupletype
from pypy.objspace.flow import model as flowmodel
from pypy.translator.simplify import eliminate_empty_blocks
from pypy.translator.unsimplify import varoftype
from pypy.rpython.module.support import init_opaque_object
from pypy.rpython.module.support import to_opaque_object, from_opaque_object
from pypy.rpython.module.support import LLSupport
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.lltypesystem.rclass import fishllattr
from pypy.rpython.lltypesystem.lloperation import llop


# for debugging, sanity checks in non-RPython code
reveal = from_opaque_object

def isptrtype(gv_type):
    c = from_opaque_object(gv_type)
    return isinstance(c.value, lltype.Ptr)

def newblock():
    block = flowmodel.Block([])
    return to_opaque_object(block)

def newgraph(gv_FUNCTYPE, name):
    FUNCTYPE = from_opaque_object(gv_FUNCTYPE).value
    # 'name' is just a way to track things
    if not isinstance(name, str):
        name = LLSupport.from_rstr(name)
    inputargs = []
    erasedinputargs = []
    for ARG in FUNCTYPE.ARGS:
        v = flowmodel.Variable()
        v.concretetype = ARG
        inputargs.append(v)
        v = flowmodel.Variable()
        v.concretetype = lltype.erasedType(ARG)
        erasedinputargs.append(v)
    startblock = flowmodel.Block(inputargs)
    # insert an exploding operation here which is removed by
    # builder.end() to ensure that builder.end() is actually called.
    startblock.operations.append(
        flowmodel.SpaceOperation("debug_assert",
                                 [flowmodel.Constant(False, lltype.Bool),
                                  flowmodel.Constant("you didn't call builder.end()?",
                                                     lltype.Void)],
                                 varoftype(lltype.Void)))
    return_var = flowmodel.Variable()
    return_var.concretetype = FUNCTYPE.RESULT
    graph = flowmodel.FunctionGraph(name, startblock, return_var)
    v1 = flowmodel.Variable()
    v1.concretetype = lltype.erasedType(FUNCTYPE.RESULT)
    graph.prereturnblock = flowmodel.Block([v1])
    casting_link(graph.prereturnblock, [v1], graph.returnblock)
    substartblock = flowmodel.Block(erasedinputargs)
    casting_link(graph.startblock, inputargs, substartblock)
    fptr = lltype.functionptr(FUNCTYPE, name,
                              graph=graph)
    return genconst(fptr)

def _getgraph(gv_func):
     graph = from_opaque_object(gv_func).value._obj.graph
     return graph

def end(gv_func):
    graph = _getgraph(gv_func)
    _buildgraph(graph)

def getstartblock(gv_func):
    graph = _getgraph(gv_func)
    [link] = graph.startblock.exits
    substartblock = link.target
    return to_opaque_object(substartblock)

def geninputarg(block, gv_CONCRETE_TYPE):
    block = from_opaque_object(block)
    assert not block.operations, "block already contains operations"
    assert block.exits == [], "block already closed"
    CONCRETE_TYPE = from_opaque_object(gv_CONCRETE_TYPE).value
    v = flowmodel.Variable()
    v.concretetype = lltype.erasedType(CONCRETE_TYPE)
    block.inputargs.append(v)
    return to_opaque_object(v)

def getinputarg(block, i):
    block = from_opaque_object(block)
    v = block.inputargs[i]
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

def cast(block, gv_TYPE, gv_var):
    TYPE = from_opaque_object(gv_TYPE).value
    v = from_opaque_object(gv_var)
    if TYPE != v.concretetype:
        if TYPE is llmemory.GCREF or v.concretetype is llmemory.GCREF:
            lltype.cast_opaque_ptr(TYPE, v.concretetype._defl()) # sanity check
            opname = 'cast_opaque_ptr'
        else:
            assert v.concretetype == lltype.erasedType(TYPE)
            opname = 'cast_pointer'
        block = from_opaque_object(block)
        v2 = flowmodel.Variable()
        v2.concretetype = TYPE
        op = flowmodel.SpaceOperation(opname, [v], v2)
        block.operations.append(op)
        v = v2
    return to_opaque_object(v)

def erasedvar(v, block):
    T = lltype.erasedType(v.concretetype)
    if T != v.concretetype:
        v2 = flowmodel.Variable()
        v2.concretetype = T
        op = flowmodel.SpaceOperation("cast_pointer", [v], v2)
        block.operations.append(op)
        return v2
    return v

def genop(block, opname, vars_gv, gv_RESULT_TYPE):
    # 'opname' is a constant string
    # gv_RESULT_TYPE comes from constTYPE
    if not isinstance(opname, str):
        opname = LLSupport.from_rstr(opname)
    block = from_opaque_object(block)
    assert block.exits == [], "block already closed"
    opvars = _inputvars(vars_gv)
    if gv_RESULT_TYPE is guess:
        RESULT_TYPE = guess_result_type(opname, opvars)
    elif isinstance(gv_RESULT_TYPE, lltype.LowLevelType):
        RESULT_TYPE = gv_RESULT_TYPE
    else:
        RESULT_TYPE = from_opaque_object(gv_RESULT_TYPE).value
    v = flowmodel.Variable()
    v.concretetype = RESULT_TYPE
    op = flowmodel.SpaceOperation(opname, opvars, v)
    block.operations.append(op)
    return to_opaque_object(erasedvar(v, block))

RESULT_TYPES = {
    'cast_ptr_to_int': lltype.Signed,
    }

def guess_result_type(opname, opvars):
    if opname.endswith('_zer'):   # h
        opname = opname[:-4]      # a
    if opname.endswith('_ovf'):   # c
        opname = opname[:-4]      # k
    if opname in RESULT_TYPES:
        return RESULT_TYPES[opname]
    op = getattr(llop, opname)
    need_result_type = getattr(op.fold, 'need_result_type', False)
    assert not need_result_type, ("cannot guess the result type of %r"
                                  % (opname,))
    examples = []
    for v in opvars:
        example = v.concretetype._example()
        if isinstance(v.concretetype, lltype.Primitive):
            if example == 0:
                example = type(example)(1)     # to avoid ZeroDivisionError
        examples.append(example)
    try:
        result = op.fold(*examples)
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception, e:
        assert 0, "failed to guess the type of %s: %s" % (opname, e)
    return lltype.typeOf(result)

def genconst(llvalue):
    T = lltype.typeOf(llvalue)
    T1 = lltype.erasedType(T)
    if T1 != T:
        llvalue = lltype.cast_pointer(T1, llvalue)
    v = flowmodel.Constant(llvalue)
    v.concretetype = T1
    if v.concretetype == lltype.Void: # XXX genconst should not really be used for Void constants
        assert not isinstance(llvalue, str) and not isinstance(llvalue, lltype.LowLevelType)
    return to_opaque_object(v)

def genzeroconst(gv_TYPE):
    TYPE = from_opaque_object(gv_TYPE).value
    TYPE = lltype.erasedType(TYPE)
    c = flowmodel.Constant(TYPE._defl())
    c.concretetype = TYPE
    return to_opaque_object(c)

def _generalcast(T, value):
    if isinstance(T, lltype.Ptr):
        return lltype.cast_pointer(T, value)
    elif T == llmemory.Address:
        return llmemory.cast_ptr_to_adr(value)
    else:
        T1 = lltype.typeOf(value)
        if T1 is llmemory.Address:
            value = llmemory.cast_adr_to_int(value)
        elif isinstance(T1, lltype.Ptr):
            value = lltype.cast_ptr_to_int(value)
        else:
            value = value
        return lltype.cast_primitive(T, value)    

def revealconst(T, gv_value):
    c = from_opaque_object(gv_value)
    assert isinstance(c, flowmodel.Constant)
    return _generalcast(T, c.value)

def revealconstrepr(gv_value):
    c = from_opaque_object(gv_value)
    return LLSupport.to_rstr(repr(c.value))

def isconst(gv_value):
    c = from_opaque_object(gv_value)
    return isinstance(c, flowmodel.Constant)


# XXX
# temporary interface; it's unclear if genop itself should change to
# ease dinstinguishing Void special args from the rest. Or there
# should be variation for the ops involving them

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

def closeblock1(block):
    block = from_opaque_object(block)
    link = flowmodel.Link([], None)
    block.closeblock(link)
    return to_opaque_object(link)

def closeblock2(block, exitswitch):
    block = from_opaque_object(block)
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

_color_num = 1
_color_den = 2
def getcolor():
    global _color_den, _color_num
    import colorsys
    hue = _color_num/float(_color_den)
    _color_num +=2
    if _color_num > _color_den:
        _color_num = 1
        _color_den *= 2
    rgb = list(colorsys.hsv_to_rgb(hue, 0.10, 1.0))
    return '#'+''.join(['%02x' % int(p*255) for p in rgb])
    
def closeblockswitch(block, exitswitch):
    block = from_opaque_object(block)
    block.blockcolor = getcolor()
    exitswitch = from_opaque_object(exitswitch)
    assert isinstance(exitswitch, flowmodel.Variable)
    TYPE = exitswitch.concretetype
    if isinstance(TYPE, lltype.Ptr):
        # XXX hack!
        v1 = varoftype(lltype.Signed)
        block.operations.append(flowmodel.SpaceOperation(
            'cast_ptr_to_int', [exitswitch], v1))
        exitswitch = v1
    block.exitswitch = exitswitch
    block.closeblock()
    return

def add_case(block, exitcase):
    block = from_opaque_object(block)
    exitcase = from_opaque_object(exitcase)
    assert isinstance(exitcase, flowmodel.Constant)
    assert isinstance(block.exitswitch, flowmodel.Variable)
    case_link = flowmodel.Link([], None)
    exitvalue = exitcase.value
    if isinstance(lltype.typeOf(exitvalue), lltype.Ptr):
        # XXX hack!
        exitvalue = lltype.cast_ptr_to_int(exitvalue)
    case_link.exitcase = exitvalue
    case_link.llexitcase = exitvalue
    if block.exits and block.exits[-1].exitcase == 'default':
        exits = block.exits[:-1] + (case_link,) + block.exits[-1:]
    else:
        exits = block.exits + (case_link,)
    block.recloseblock(*exits)
    return to_opaque_object(case_link)

def add_default(block):
    block = from_opaque_object(block)
    assert isinstance(block.exitswitch, flowmodel.Variable)
    default_link = flowmodel.Link([], None)
    default_link.exitcase = 'default'
    default_link.llexitcase = None
    if block.exits and block.exits[-1].exitcase == 'default':
        raise ValueError
    else:
        exits = block.exits + (default_link,)
    block.recloseblock(*exits)
    return to_opaque_object(default_link)

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
        assert link.target is None     # link already closed
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

def closelink(link, vars, targetblock):
    link = from_opaque_object(link)
    targetblock = from_opaque_object(targetblock)
    vars = _inputvars(vars)
    _closelink(link, vars, targetblock)

def closereturnlink(link, returnvar, gv_func):
    returnvar = from_opaque_object(returnvar)
    link = from_opaque_object(link)
    graph = _getgraph(gv_func)
    _closelink(link, [returnvar], graph.prereturnblock)

def closelinktofreshblock(link, inputargs=None, otherlink=None):
    link = from_opaque_object(link)
    prevblockvars = link.prevblock.getvariables()
    # the next block's inputargs come from 'inputargs' if specified
    if inputargs is None:
        inputvars = prevblockvars
    else:
        inputvars = _inputvars(inputargs)
        inputvars = dict.fromkeys(inputvars).keys()
    # the link's arguments are the same as the inputvars, except
    # if otherlink is specified, in which case they are copied from otherlink
    if otherlink is None:
        linkvars = list(inputvars)
    else:
        otherlink = from_opaque_object(otherlink)
        linkvars = list(otherlink.args)
    # check linkvars for consistency
    existing_vars = dict.fromkeys(prevblockvars)
    for v in inputvars:
        assert isinstance(v, flowmodel.Variable)
    for v in linkvars:
        assert v in existing_vars

    nextblock = flowmodel.Block(inputvars)
    link.args = linkvars
    link.target = nextblock
    return to_opaque_object(nextblock)

def casting_link(source, sourcevars, target):
    assert len(sourcevars) == len(target.inputargs)
    linkargs = []
    for v, target_v in zip(sourcevars, target.inputargs):
        if v.concretetype == target_v.concretetype:
            linkargs.append(v)
        else:
            erasedv = flowmodel.Variable()
            erasedv.concretetype = target_v.concretetype
            source.operations.append(flowmodel.SpaceOperation('cast_pointer',
                                                              [v],
                                                              erasedv))
            linkargs.append(erasedv)
    source.closeblock(flowmodel.Link(linkargs, target))

# ____________________________________________________________

class PseudoRTyper(object):
    def __init__(self):
        from pypy.rpython.typesystem import LowLevelTypeSystem
        self.type_system = LowLevelTypeSystem.instance

def fixduplicatevars(graph):
    # just rename all vars in all blocks
    try:
        done = graph._llimpl_blocks_already_renamed
    except AttributeError:
        done = graph._llimpl_blocks_already_renamed = {}

    for block in graph.iterblocks():
        if block not in done:
            mapping = {}
            for a in block.inputargs:
                mapping[a] = a1 = flowmodel.Variable(a)
                a1.concretetype = a.concretetype
            block.renamevariables(mapping)
            done[block] = True

def _buildgraph(graph):
    assert graph.startblock.operations[0].opname == 'debug_assert'
    del graph.startblock.operations[0]
    # rgenop makes graphs that use the same variable in several blocks,
    fixduplicatevars(graph)                             # fix this now
    flowmodel.checkgraph(graph)
    eliminate_empty_blocks(graph)
    # we cannot call join_blocks(graph) here!  It has a subtle problem:
    # it copies operations between blocks without renaming op.result.
    # See test_promotion.test_many_promotions for a failure.
    graph.rgenop = True
    return graph

def buildgraph(graph, FUNCTYPE):
    graph = from_opaque_object(graph)
    return _buildgraph(graph)

def testgengraph(gengraph, args, viewbefore=False, executor=LLInterpreter):
    if viewbefore:
        gengraph.show()
    llinterp = executor(PseudoRTyper())
    return llinterp.eval_graph(gengraph, args)
    
def runblock(graph, FUNCTYPE, args,
             viewbefore=False, executor=LLInterpreter):
    graph = buildgraph(graph, FUNCTYPE)
    return testgengraph(graph, args, viewbefore, executor)

def show_incremental_progress(gv_func):
    from pypy import conftest
    graph = _getgraph(gv_func)
    fixduplicatevars(graph)
    flowmodel.checkgraph(graph)
    if conftest.option.view:
        eliminate_empty_blocks(graph)
        graph.show()

# ____________________________________________________________
# RTyping of the above functions

from pypy.rpython.extfunctable import declareptrtype

blocktypeinfo = declareptrtype(flowmodel.Block, "Block")
consttypeinfo = declareptrtype(flowmodel.Constant, "ConstOrVar")
vartypeinfo   = declareptrtype(flowmodel.Variable, "ConstOrVar")
vartypeinfo.set_lltype(consttypeinfo.get_lltype())   # force same lltype
linktypeinfo  = declareptrtype(flowmodel.Link, "Link")
graphtypeinfo = declareptrtype(flowmodel.FunctionGraph, "FunctionGraph")

CONSTORVAR = lltype.Ptr(consttypeinfo.get_lltype())
BLOCK = lltype.Ptr(blocktypeinfo.get_lltype())
LINK = lltype.Ptr(linktypeinfo.get_lltype())
GRAPH = lltype.Ptr(graphtypeinfo.get_lltype())

# support constants and types

nullvar = lltype.nullptr(CONSTORVAR.TO)
nullblock = lltype.nullptr(BLOCK.TO)
nulllink = lltype.nullptr(LINK.TO)
nullgraph = lltype.nullptr(GRAPH.TO)
gv_Void = constTYPE(lltype.Void)

dummy_placeholder = placeholder(None)
guess = placeholder('guess')


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
                                             _callable=func, _debugexc=True)
                cfunc = hop.inputconst(lltype.Ptr(FUNCTYPE), funcptr)
                return hop.genop('direct_call', [cfunc] + args_v, hop.r_result)

# annotations
from pypy.annotation import model as annmodel

s_ConstOrVar = annmodel.SomePtr(CONSTORVAR)#annmodel.SomeExternalObject(flowmodel.Variable)
s_Link = annmodel.SomePtr(LINK)#annmodel.SomeExternalObject(flowmodel.Link)
s_LinkPair = annmodel.SomeTuple([s_Link, s_Link])
s_Block = annmodel.SomePtr(BLOCK)
s_Graph = annmodel.SomePtr(GRAPH)

setannotation(newblock, s_Block)
setannotation(newgraph, s_ConstOrVar)
setannotation(getstartblock, s_Block)
setannotation(geninputarg, s_ConstOrVar)
setannotation(getinputarg, s_ConstOrVar)
setannotation(genop, s_ConstOrVar)
setannotation(end, None)
setannotation(genconst, s_ConstOrVar)
setannotation(genzeroconst, s_ConstOrVar)
setannotation(cast, s_ConstOrVar)
setannotation(revealconst, lambda s_T, s_gv: annmodel.lltype_to_annotation(
                                                  s_T.const))
from pypy.rpython.lltypesystem.rstr import STR
setannotation(revealconstrepr, annmodel.SomePtr(lltype.Ptr(STR)))
setannotation(isconst, annmodel.SomeBool())
setannotation(closeblock1, s_Link)
setannotation(closeblock2, s_LinkPair)
setannotation(closeblockswitch, None)
setannotation(add_case, s_Link)
setannotation(add_default, s_Link)
setannotation(closelink, None)
setannotation(closereturnlink, None)
setannotation(closelinktofreshblock, s_Block)

setannotation(isptrtype, annmodel.SomeBool())

# XXX(for now) void constant constructors
setannotation(constFieldName, s_ConstOrVar, specialize_as_constant=True)
setannotation(constTYPE,      s_ConstOrVar, specialize_as_constant=True)
#setannotation(placeholder,    s_ConstOrVar, specialize_as_constant=True)

setannotation(show_incremental_progress, None)

# read frame var support

def get_frame_info(block, vars_gv):
    genop(block, 'frame_info', vars_gv, lltype.Void)
    block = from_opaque_object(block)
    frame_info = block.operations[-1]
    return lltype.opaqueptr(llmemory.GCREF.TO, 'frame_info',
                            info=frame_info)

setannotation(get_frame_info, annmodel.SomePtr(llmemory.GCREF))

def read_frame_var(T, base, info, index):
    vars = info._obj.info.args
    v = vars[index]
    if isinstance(v, flowmodel.Constant):
        val = v.value
    else:
        llframe = base.ptr
        val = llframe.bindings[v]
    return _generalcast(T, val)

setannotation(read_frame_var, lambda s_T, s_base, s_info, s_index:
              annmodel.lltype_to_annotation(s_T.const))

def write_frame_var(base, info, index, value):
    vars = info._obj.info.args
    v = vars[index]
    assert isinstance(v, flowmodel.Variable)
    llframe = base.ptr
    value = _generalcast(v.concretetype, value)
    llframe.bindings[v] = value


setannotation(write_frame_var, None)
