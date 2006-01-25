"""
Functions that generate flow graphs and operations.
The functions below produce L2 graphs, but they define an interface
that can be used to produce any other kind of graph.
"""

from pypy.rpython.lltypesystem import lltype
from pypy.objspace.flow import model as flowmodel


def newblock():
    return flowmodel.Block([])

def geninputarg(block, CONCRETE_TYPE):
    v = flowmodel.Variable()
    v.concretetype = CONCRETE_TYPE
    block.inputargs.append(v)
    return v

def genop(block, opname, vars, RESULT_TYPE):
    for v in vars:
        assert isinstance(v, (flowmodel.Constant, flowmodel.Variable))
        
    v = flowmodel.Variable()
    v.concretetype = RESULT_TYPE
    op = flowmodel.SpaceOperation(opname, vars, v)
    block.operations.append(op)
    return v

def genconst(block, llvalue):
    v = flowmodel.Constant(llvalue)
    v.concretetype = lltype.typeOf(llvalue)
    return v

def addconst(block, const):
    assert isinstance(const, flowmodel.Constant)
    return const

def closeblock1(block):
    link = flowmodel.Link([], None)
    block.closeblock(link)
    return link

def closeblock2(block, exitswitch):
    block.exitswitch = exitswitch
    false_link = flowmodel.Link([], None)
    false_link.exitcase = False
    false_link.llexitcase = False
    true_link = flowmodel.Link([], None)
    true_link.exitcase = True
    true_link.llexitcase = True
    block.closeblock(false_link, true_link)
    return false_link, true_link

def closelink(link, vars, targetblock):
    if isinstance(link, flowmodel.Link):
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

def closereturnlink(link, returnvar):
    v = flowmodel.Variable()
    v.concretetype = returnvar.concretetype
    pseudoreturnblock = flowmodel.Block([v])
    pseudoreturnblock.operations = ()
    closelink(link, [returnvar], pseudoreturnblock)

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

def runblock(block, args):
    from pypy.rpython.llinterp import LLInterpreter
    graph = flowmodel.FunctionGraph('?', block)
    _patchgraph(graph)
    flowmodel.checkgraph(graph)
    llinterp = LLInterpreter(PseudoRTyper())
    return llinterp.eval_graph(graph, args)
