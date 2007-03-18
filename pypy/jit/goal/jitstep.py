import types
from pypy.module.pypyjit.interp_jit import PORTAL

from pypy.objspace.flow.model import checkgraph
from pypy.translator.translator import graphof
from pypy.annotation.specialize import getuniquenondirectgraph
from pypy.jit.hintannotator.annotator import HintAnnotator, HintAnnotatorPolicy
from pypy.jit.hintannotator.model import OriginFlags, SomeLLAbstractConstant

PORTAL = getattr(PORTAL, 'im_func', PORTAL)


class PyPyHintAnnotatorPolicy(HintAnnotatorPolicy):

    def __init__(self, timeshift_graphs):
        HintAnnotatorPolicy.__init__(self, novirtualcontainer = True,
                                           oopspec = True)
        self.timeshift_graphs = timeshift_graphs

    def look_inside_graph(self, graph):
        if graph in self.timeshift_graphs:
            return self.timeshift_graphs[graph]
        try:
            func = graph.func
        except AttributeError:
            return True
        mod = func.__module__ or '?'
        if mod.startswith('pypy.objspace'):
            return False
        if mod.startswith('pypy._cache'):
            return False
        if mod.startswith('pypy.interpreter.astcompiler'):
            return False
        if mod.startswith('pypy.interpreter.pyparser'):
            return False
        if mod.startswith('pypy.module.'):
            if not mod.startswith('pypy.module.pypyjit.'):
                return False
        if mod in forbidden_modules:
            return False
        if func.__name__.startswith('_mm_') or '_mth_mm_' in func.__name__:
            return False
        if func.__name__.startswith('fastfunc_'):
            return False
        return True

forbidden_modules = {'pypy.interpreter.gateway': True,
                     #'pypy.interpreter.baseobjspace': True,
                     'pypy.interpreter.typedef': True,
                     'pypy.interpreter.eval': True,
                     'pypy.interpreter.function': True,
                     'pypy.interpreter.pytraceback': True,
                     }

def enumerate_reachable_graphs(translator, startgraph):
    from pypy.translator.backendopt.support import find_calls_from
    pending = [(startgraph, None)]
    yield pending[0]
    seen = {startgraph: True}
    while pending:
        yield None     # hack: a separator meaning "length increases now"
        nextlengthlist = []
        nextseen = {}
        for node in pending:
            head, tail = node
            for block, callee in find_calls_from(translator, head):
                if callee not in seen:
                    newnode = callee, node
                    yield newnode
                    nextlengthlist.append(newnode)
                    nextseen[callee] = True
        pending = nextlengthlist
        seen.update(nextseen)
    yield None

def graphs_on_the_path_to(translator, startgraph, targetgraphs):
    targetgraphs = targetgraphs.copy()
    result = {}
    found = {}
    for node in enumerate_reachable_graphs(translator, startgraph):
        if node is None:  # hack: a separator meaning "length increases now"
            for graph in found:
                del targetgraphs[graph]
            found.clear()
            if not targetgraphs:
                return result
        elif node[0] in targetgraphs:
            found[node[0]] = True
            while node is not None:
                head, tail = node
                result[head] = True
                node = tail
    raise Exception("did not reach all targets:\nmissing %r" % (
        targetgraphs.keys(),))


def timeshift_graphs(t, portal_graph, log):
    result_graphs = {}

    bk = t.annotator.bookkeeper

    def _graph(func):
        func = getattr(func, 'im_func', func)
        desc = bk.getdesc(func)
        return getuniquenondirectgraph(desc)

    def seefunc(fromfunc, *tofuncs):
        targetgraphs = {}
        for tofunc in tofuncs:
            targetgraphs[_graph(tofunc)] = True
        graphs = graphs_on_the_path_to(t, _graph(fromfunc), targetgraphs)
        for graph in graphs:
            if graph not in result_graphs:
                log('including graph %s' % (graph,))
            result_graphs[graph] = True

    def seepath(*path):
        for i in range(1, len(path)):
            seefunc(path[i-1], path[i])

    def dontsee(func):
        result_graphs[_graph(func)] = False

    # --------------------
    import pypy
    seepath(pypy.interpreter.pyframe.PyFrame.BINARY_ADD,
            pypy.objspace.descroperation.DescrOperation.add,
            pypy.objspace.std.intobject.add__Int_Int,
            pypy.objspace.std.inttype.wrapint,
            pypy.objspace.std.intobject.W_IntObject.__init__)
    seepath(pypy.interpreter.pyframe.PyFrame.BINARY_SUBTRACT,
            pypy.objspace.descroperation.DescrOperation.sub,
            pypy.objspace.std.intobject.sub__Int_Int)
    seepath(pypy.interpreter.pyframe.PyFrame.BINARY_MULTIPLY,
            pypy.objspace.descroperation.DescrOperation.mul,
            pypy.objspace.std.intobject.mul__Int_Int)
    seepath(pypy.interpreter.pyframe.PyFrame.BINARY_AND,
            pypy.objspace.descroperation.DescrOperation.and_,
            pypy.objspace.std.intobject.and__Int_Int)
    seepath(pypy.interpreter.pyframe.PyFrame.BINARY_OR,
            pypy.objspace.descroperation.DescrOperation.or_,
            pypy.objspace.std.intobject.or__Int_Int)
    seepath(pypy.interpreter.pyframe.PyFrame.BINARY_XOR,
            pypy.objspace.descroperation.DescrOperation.xor,
            pypy.objspace.std.intobject.xor__Int_Int)
    seepath(pypy.interpreter.pyframe.PyFrame.COMPARE_OP,
            pypy.objspace.descroperation.DescrOperation.lt,
            pypy.objspace.std.intobject.lt__Int_Int)
    seepath(pypy.interpreter.pyframe.PyFrame.COMPARE_OP,
            pypy.objspace.descroperation.DescrOperation.le,
            pypy.objspace.std.intobject.le__Int_Int)
    seepath(pypy.interpreter.pyframe.PyFrame.COMPARE_OP,
            pypy.objspace.descroperation.DescrOperation.eq,
            pypy.objspace.std.intobject.eq__Int_Int)
    seepath(pypy.interpreter.pyframe.PyFrame.COMPARE_OP,
            pypy.objspace.descroperation.DescrOperation.ne,
            pypy.objspace.std.intobject.ne__Int_Int)
    seepath(pypy.interpreter.pyframe.PyFrame.COMPARE_OP,
            pypy.objspace.descroperation.DescrOperation.gt,
            pypy.objspace.std.intobject.gt__Int_Int)
    seepath(pypy.interpreter.pyframe.PyFrame.COMPARE_OP,
            pypy.objspace.descroperation.DescrOperation.ge,
            pypy.objspace.std.intobject.ge__Int_Int)
    seepath(pypy.objspace.descroperation._invoke_binop,
            pypy.objspace.descroperation._check_notimplemented)
    seepath(pypy.objspace.descroperation.DescrOperation.add,
            pypy.objspace.std.Space.type,
            pypy.objspace.std.Space.gettypeobject)
    #seepath(pypy.objspace.descroperation.DescrOperation.xxx,
    #        pypy.objspace.std.typeobject.W_TypeObject.lookup,
    #        pypy.objspace.std.typeobject.W_TypeObject.getdictvalue_w)
    seepath(pypy.objspace.descroperation.DescrOperation.add,
            pypy.objspace.std.typeobject.W_TypeObject.lookup_where,
            pypy.objspace.std.typeobject.W_TypeObject.getdictvalue_w)
    seepath(pypy.objspace.std.typeobject.W_TypeObject.lookup_where,
            pypy.objspace.std.typeobject.W_TypeObject.is_heaptype)
    seepath(pypy.objspace.descroperation.DescrOperation.add,
            pypy.objspace.std.Space.is_w)
    dontsee(pypy.interpreter.pyframe.PyFrame.execute_frame)
    # --------------------

    return result_graphs


def hintannotate(drv):
    t = drv.translator
    portal_graph = graphof(t, PORTAL)

    POLICY = PyPyHintAnnotatorPolicy(timeshift_graphs(t, portal_graph,
                                                      drv.log))

##    graphnames = [str(_g) for _g in POLICY.timeshift_graphs]
##    graphnames.sort()
##    print '-' * 20
##    for graphname in graphnames:
##        print graphname
##    print '-' * 20

    hannotator = HintAnnotator(base_translator=t, policy=POLICY)
    hs = hannotator.build_types(portal_graph,
                                [SomeLLAbstractConstant(v.concretetype,
                                                        {OriginFlags(): True})
                                 for v in portal_graph.getargs()])
    count = hannotator.bookkeeper.nonstubgraphcount
    drv.log.info('Hint-annotated %d graphs (plus %d stubs).' % (
        count, len(hannotator.translator.graphs) - count))
    n = len(list(hannotator.translator.graphs[0].iterblocks()))
    drv.log.info("portal has %d blocks" % n)
    drv.hannotator = hannotator
    #import pdb; pdb.set_trace()

def timeshift(drv):
    from pypy.tool.udir import udir
    udir.ensure(dir=1)    # fork-friendly hack
    udir.join('.lock').ensure()
    from pypy.jit.timeshifter.hrtyper import HintRTyper
    #from pypy.jit.codegen.llgraph.rgenop import RGenOp
    from pypy.jit.codegen.i386.rgenop import RI386GenOp as RGenOp
    RGenOp.MC_SIZE = 32 * 1024 * 1024     # 32MB - but supposed infinite!

    ha = drv.hannotator
    t = drv.translator
    # make the timeshifted graphs
    hrtyper = HintRTyper(ha, t.rtyper, RGenOp)
    origportalgraph = graphof(t, PORTAL)
    hrtyper.specialize(origportalgraph=origportalgraph, view=False)
        
    # XXX temp
    drv.source()
