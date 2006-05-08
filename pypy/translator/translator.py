"""PyPy Translator Frontend

The Translator is a glue class putting together the various pieces of the
translation-related code.  It can be used for interactive testing of the
translator; see pypy/bin/translatorshell.py.
"""
import autopath, os, sys, types, copy

from pypy.objspace.flow.model import *
from pypy.translator.simplify import simplify_graph
from pypy.objspace.flow import FlowObjSpace
from pypy.tool.ansi_print import ansi_log
from pypy.tool.sourcetools import nice_repr_for_func
import py
log = py.log.Producer("flowgraph") 
py.log.setconsumer("flowgraph", ansi_log) 

class TranslationContext(object):
    FLOWING_FLAGS = {
        'verbose': False,
        'simplifying': True,
        'do_imports_immediately': True,
        'builtins_can_raise_exceptions': False,
        }

    def __init__(self, **flowing_flags):
        self.flags = self.FLOWING_FLAGS.copy()
        self.flags.update(flowing_flags)
        if len(self.flags) > len(self.FLOWING_FLAGS):
            raise TypeError("unexpected keyword argument")
        self.annotator = None
        self.rtyper = None
        self.graphs = []      # [graph]
        self.callgraph = {}   # {opaque_tag: (caller-graph, callee-graph)}
        self._prebuilt_graphs = {}   # only used by the pygame viewer

        self._implicitly_called_by_externals = []

    def buildflowgraph(self, func):
        """Get the flow graph for a function."""
        if not isinstance(func, types.FunctionType):
            raise TypeError("buildflowgraph() expects a function, "
                            "got %r" % (func,))
        if func in self._prebuilt_graphs:
            graph = self._prebuilt_graphs.pop(func)
        else:
            if self.flags.get('verbose'):
                log.start(nice_repr_for_func(func))
            space = FlowObjSpace()
            space.__dict__.update(self.flags)   # xxx push flags there
            if self.annotator:
                self.annotator.policy._adjust_space_config(space)
            graph = space.build_flow(func)
            if self.flags.get('simplifying'):
                simplify_graph(graph)
            if self.flags.get('verbose'):
                log.done(func.__name__)
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
                                   type_system = type_system)
        return self.rtyper

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

    def viewcg(self):
        """Shows the whole call graph and the class hierarchy, based on
        the computed annotations."""
        from pypy.translator.tool.graphpage import TranslatorPage
        TranslatorPage(self).display()



# _______________________________________________________________
# testing helper

def graphof(translator, func):
    result = []
    for graph in translator.graphs:
        if getattr(graph, 'func', None) is func:
            result.append(graph)
    assert len(result) == 1
    return result[0]
