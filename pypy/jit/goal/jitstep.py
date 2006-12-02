from pypy.interpreter.pyframe import PyFrame

from pypy.translator.translator import graphof
from pypy.jit.hintannotator.annotator import HintAnnotator, HintAnnotatorPolicy
from pypy.jit.hintannotator.model import OriginFlags, SomeLLAbstractConstant

PORTAL = PyFrame.dispatch_bytecode.im_func
#from pypy.jit.goal.x import evaluate as PORTAL


class PyPyHintAnnotatorPolicy(HintAnnotatorPolicy):

    def look_inside_graph(self, graph):
        func = graph.func
        mod = func.__module__ or '?'
        if mod.startswith('pypy.objspace.'):
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
    print 'Hint-annotated %d graphs.' % (len(hannotator.translator.graphs),)
    drv.hannotator = hannotator


def timeshift(drv):
    from pypy.jit.timeshifter.hrtyper import HintRTyper
    from pypy.jit.codegen.llgraph.rgenop import RGenOp    # for now
    ha = drv.hannotator
    t = drv.translator
    # make the timeshifted graphs
    hrtyper = HintRTyper(ha, t.rtyper, RGenOp)
    origportalgraph = graphof(t, PORTAL)
    hrtyper.specialize(origportalgraph=origportalgraph, view=False)
    for graph in ha.translator.graphs:
        checkgraph(graph)
        t.graphs.append(graph)
    import pdb; pdb.set_trace()
