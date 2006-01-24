"""
Functions that generate flow graphs and operations.
The functions below produce L2 graphs, but they define an interface
that can be used to produce any other kind of graph.
"""

from pypy.rpython.lltypesystem import lltype
from pypy.objspace.flow import model as flowmodel


def newgraph(name):
    startblock_to_throw_away = flowmodel.Block([])   # grumble
    return flowmodel.FunctionGraph(name, startblock_to_throw_away)

def newblock():
    return flowmodel.Block([])

def geninputarg(block, CONCRETE_TYPE):
    v = flowmodel.Variable()
    v.concretetype = CONCRETE_TYPE
    block.inputargs.append(v)
    return v

def genop(block, opname, vars, RESULT_TYPE):
    v = flowmodel.Variable()
    v.concretetype = RESULT_TYPE
    op = flowmodel.SpaceOperation(opname, vars, v)
    block.operations.append(op)
    return v

def genconst(block, llvalue):
    v = flowmodel.Constant(llvalue)
    v.concretetype = lltype.typeOf(llvalue)
    return v

def newlink(block, vars):
    return flowmodel.Link(vars, None)

def newreturnlink(block, var):
    v = flowmodel.Variable()
    v.concretetype = var.concretetype
    pseudoreturnblock = flowmodel.Block([v])
    pseudoreturnblock.operations = ()
    return flowmodel.Link([var], pseudoreturnblock)

def closeblock1(block, link):
    block.closeblock(link)

def closeblock2(block, exitswitch, false_link, true_link):
    block.exitswitch = exitswitch
    false_link.exitcase = False
    false_link.llexitcase = False
    true_link.exitcase = True
    true_link.llexitcase = True
    block.closeblock(false_link, true_link)

def closelink(link, targetblock):
    if isinstance(link, flowmodel.Link):
        assert link.target is None, "%r already closed" % (link,)
        assert ([v.concretetype for v in link.args] ==
                [v.concretetype for v in targetblock.inputargs])
        link.target = targetblock
    elif isinstance(link, flowmodel.FunctionGraph):
        graph = link
        graph.startblock = targetblock
        targetblock.isstartblock = True
    else:
        raise TypeError

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

def runlink(startlink, args):
    from pypy.rpython.llinterp import LLInterpreter
    assert isinstance(startlink, flowmodel.FunctionGraph), "XXX"
    graph = startlink  # for now
    _patchgraph(graph)
    flowmodel.checkgraph(graph)
    llinterp = LLInterpreter(PseudoRTyper())
    return llinterp.eval_graph(graph, args)
