"""PyPy Translator Frontend

The Translator is a glue class putting together the various pieces of the
translation-related code.  It can be used for interactive testing of the
translator; see pypy/bin/translatorshell.py.
"""
import autopath, os, sys, types, copy

from pypy.translator import simplify
from pypy.objspace.flow.model import FunctionGraph, checkgraph, Block
from pypy.tool.ansi_print import ansi_log
from pypy.tool.sourcetools import nice_repr_for_func
from pypy.config.pypyoption import pypy_optiondescription
from pypy.config.translationoption import get_combined_translation_config
from pypy.config.translationoption import get_platform
import py
log = py.log.Producer("flowgraph")
py.log.setconsumer("flowgraph", ansi_log)

class TranslationContext(object):
    FLOWING_FLAGS = {
        'verbose': False,
        'simplifying': True,
        'builtins_can_raise_exceptions': False,
        'list_comprehension_operations': False,   # True, - not super-tested
        }

    def __init__(self, config=None, **flowing_flags):
        if config is None:
            from pypy.config.pypyoption import get_pypy_config
            config = get_pypy_config(translating=True)
        # ZZZ should go away in the end
        for attr in ['verbose', 'simplifying',
                     'builtins_can_raise_exceptions',
                     'list_comprehension_operations']:
            if attr in flowing_flags:
                setattr(config.translation, attr, flowing_flags[attr])
        self.config = config
        self.platform = get_platform(config)
        self.create_flowspace_config()
        self.annotator = None
        self.rtyper = None
        self.exceptiontransformer = None
        self.graphs = []      # [graph]
        self.callgraph = {}   # {opaque_tag: (caller-graph, callee-graph)}
        self._prebuilt_graphs = {}   # only used by the pygame viewer

    def create_flowspace_config(self):
        # XXX this is a hack: we create a new config, which is only used
        # for the flow object space. The problem is that the flow obj space
        # needs an objspace config, but the thing we are translating might not
        # have one (or worse we are translating pypy and the flow space picks
        # up strange options of the pypy we are translating). Therefore we need
        # to construct this new config
        self.flowconfig = get_combined_translation_config(
                pypy_optiondescription, self.config, translating=True)
        self.flowconfig.objspace.name = "flow"

    def buildflowgraph(self, func, mute_dot=False):
        """Get the flow graph for a function."""
        if not isinstance(func, types.FunctionType):
            raise TypeError("buildflowgraph() expects a function, "
                            "got %r" % (func,))
        if func in self._prebuilt_graphs:
            graph = self._prebuilt_graphs.pop(func)
        else:
            if self.config.translation.verbose:
                log.start(nice_repr_for_func(func))
            from pypy.objspace.flow.objspace import FlowObjSpace
            space = FlowObjSpace(self.flowconfig)
            if self.annotator:
                # ZZZ
                self.annotator.policy._adjust_space_config(space)
            elif hasattr(self, 'no_annotator_but_do_imports_immediately'):
                space.do_imports_immediately = (
                    self.no_annotator_but_do_imports_immediately)
            graph = space.build_flow(func)
            if self.config.translation.simplifying:
                simplify.simplify_graph(graph)
            if self.config.translation.list_comprehension_operations:
                simplify.detect_list_comprehension(graph)
            if self.config.translation.verbose:
                log.done(func.__name__)
            elif not mute_dot:
                log.dot()
            self.graphs.append(graph)   # store the graph in our list
        return graph

    def update_call_graph(self, caller_graph, callee_graph, position_tag):
        # update the call graph
        key = caller_graph, callee_graph, position_tag
        self.callgraph[key] = caller_graph, callee_graph

    def buildannotator(self, policy=None):
        if self.annotator is not None:
            raise ValueError("we already have an annotator")
        from pypy.annotation.annrpython import RPythonAnnotator
        self.annotator = RPythonAnnotator(self, policy=policy)
        return self.annotator

    def buildrtyper(self, type_system="lltype"):
        if self.annotator is None:
            raise ValueError("no annotator")
        if self.rtyper is not None:
            raise ValueError("we already have an rtyper")
        from pypy.rpython.rtyper import RPythonTyper
        self.rtyper = RPythonTyper(self.annotator,
                                   type_system=type_system)
        return self.rtyper

    def getexceptiontransformer(self):
        if self.rtyper is None:
            raise ValueError("no rtyper")
        if self.exceptiontransformer is not None:
            return self.exceptiontransformer
        from pypy.translator.exceptiontransform import ExceptionTransformer
        self.exceptiontransformer = ExceptionTransformer(self)
        return self.exceptiontransformer

    def checkgraphs(self):
        for graph in self.graphs:
            checkgraph(graph)

    # debug aids

    def about(self, x, f=None):
        """Interactive debugging helper """
        if f is None:
            f = sys.stdout
        if isinstance(x, Block):
            for graph in self.graphs:
                if x in graph.iterblocks():
                    print >>f, '%s is a %s' % (x, x.__class__)
                    print >>f, 'in %s' % (graph,)
                    break
            else:
                print >>f, '%s is a %s at some unknown location' % (
                    x, x.__class__.__name__)
            print >>f, 'containing the following operations:'
            for op in x.operations:
                print >>f, "   ",op
            print >>f, '--end--'
            return
        raise TypeError, "don't know about %r" % x


    def view(self):
        """Shows the control flow graph with annotations if computed.
        Requires 'dot' and pygame."""
        from pypy.translator.tool.graphpage import FlowGraphPage
        FlowGraphPage(self).display()

    def viewcg(self, center_graph=None):
        """Shows the whole call graph and the class hierarchy, based on
        the computed annotations."""
        from pypy.translator.tool.graphpage import TranslatorPage
        TranslatorPage(self, center_graph=center_graph).display()



# _______________________________________________________________
# testing helper

def graphof(translator, func):
    if isinstance(func, FunctionGraph):
        return func
    result = []
    for graph in translator.graphs:
        if getattr(graph, 'func', None) is func:
            result.append(graph)
    assert len(result) == 1
    return result[0]

TranslationContext._graphof = graphof
