from pypy.interpreter.pyopcode import PyInterpFrame

from pypy.translator.translator import graphof
from pypy.jit.hintannotator.annotator import HintAnnotator, HintAnnotatorPolicy
from pypy.jit.hintannotator.model import OriginFlags, SomeLLAbstractConstant

PORTAL = PyInterpFrame.dispatch_translated.im_func
#from pypy.jit.goal.x import evaluate as PORTAL


class PyPyHintAnnotatorPolicy(HintAnnotatorPolicy):

    def look_inside_graph(self, graph):
        func = graph.func
        mod = func.__module__ or '?'
        if mod.startswith('pypy.objspace.'):
            return False
        if mod.startswith('pypy.module.'):
            return False
        return True

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
    import pdb; pdb.set_trace()
