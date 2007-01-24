from pypy.module.pypyjit.interp_jit import PORTAL

from pypy.objspace.flow.model import checkgraph
from pypy.translator.translator import graphof
from pypy.jit.hintannotator.annotator import HintAnnotator, HintAnnotatorPolicy
from pypy.jit.hintannotator.model import OriginFlags, SomeLLAbstractConstant

PORTAL = getattr(PORTAL, 'im_func', PORTAL)


class PyPyHintAnnotatorPolicy(HintAnnotatorPolicy):

    def look_inside_graph(self, graph):
        try:
            func = graph.func
        except AttributeError:
            return True
        mod = func.__module__ or '?'
        if mod.startswith('pypy.objspace'):
            return False
        if mod.startswith('pypy.module.'):
            return False
        if mod in forbidden_modules:
            return False
        return True

forbidden_modules = {'pypy.interpreter.gateway': True,
                     'pypy.interpreter.baseobjspace': True,
                     'pypy.interpreter.typedef': True,
                     'pypy.interpreter.eval': True,
                     'pypy.interpreter.function': True,
                     'pypy.interpreter.pytraceback': True,
                     }

POLICY = PyPyHintAnnotatorPolicy(novirtualcontainer = True,
                                 oopspec = True)

def hintannotate(drv):
    t = drv.translator
    portal_graph = graphof(t, PORTAL)
    
    hannotator = HintAnnotator(base_translator=t, policy=POLICY)
    hs = hannotator.build_types(portal_graph,
                                [SomeLLAbstractConstant(v.concretetype,
                                                        {OriginFlags(): True})
                                 for v in portal_graph.getargs()])
    drv.log.info('Hint-annotated %d graphs.' % (
        len(hannotator.translator.graphs),))
    n = len(list(hannotator.translator.graphs[0].iterblocks()))
    drv.log.info("portal has %d blocks" % n)
    drv.hannotator = hannotator

def timeshift(drv):
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
    for graph in ha.translator.graphs:
        checkgraph(graph)
        t.graphs.append(graph)
        
    # XXX temp
    drv.compile()
