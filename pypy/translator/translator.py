"""
Glue script putting together the pieces of the translator.
Can also be used for interactive testing of the translator, when run as:

    python -i translator.py

Example:

    def f1(x):
        total = 0
        for i in range(1, x+1):
            total = total + i
        return total

    t = Translator(f1)
    t.gv()    # show the control flow graph -- requires 'dot' and 'gv'
    
    t.simplify()
    t.gv()
    print t.pyrex()
    
    a = t.annotate([int])   # the list is the input args types
    print t.pyrex()
    
    a.simplify()            # simplifications done by the Annotator
    print t.pyrex()

    f = t.compile()
    print f(10)
"""

import autopath

from pypy.translator.flowmodel import *
from pypy.translator.annset import AnnotationSet, Cell
from pypy.translator.annotation import Annotator
from pypy.translator.simplify import simplify_graph
from pypy.translator.genpyrex import GenPyrex
from pypy.translator.gencl import GenCL
from pypy.translator.test.buildpyxmodule import make_module_from_pyxstring
from pypy.objspace.flow import FlowObjSpace


class Translator:
    # XXX this class should handle recursive analysis of functions called
    #     by the entry point function.

    def __init__(self, func):
        self.entrypoint = func
        self.annotator = None
        space = FlowObjSpace()
        self.flowgraph = space.build_flow(func)
        try:
            import inspect
            self.flowgraph.source = inspect.getsource(func)
        except IOError:
            pass   # e.g. when func is defined interactively

    def gv(self):
        """Show the control flow graph -- requires 'dot' and 'gv'."""
        import os
        from pypy.translator.test.make_dot import make_dot
        from pypy.tool.udir import udir
        dest = make_dot(self.flowgraph, udir, 'ps')
        os.system('gv %s' % str(dest))

    def simplify(self):
        self.flowgraph = simplify_graph(self.flowgraph)

    def annotate(self, input_args_types):
        self.annotator = Annotator(self.flowgraph)
        self.annotator.build_types(input_args_types)
        return self.annotator

    def pyrex(self):
        g = GenPyrex(self.flowgraph)
        if self.annotator:
            g.setannotator(self.annotator)
        return g.emitcode()

    def cl(self):
        g = GenCL(self.flowgraph)
        return g.emitcode()

    def compile(self):
        from pypy.tool.udir import udir
        name = self.entrypoint.func_name
        pyxcode = self.pyrex()
        mod = make_module_from_pyxstring(name, udir, pyxcode)
        return getattr(mod, name)


if __name__ == '__main__':
    def f1(x):
        total = 0
        for i in range(1, x+1):
            total = total + i
        return total

    def f2(x):
        total = 0
        while x > 0:
            total = total + x
            x = x - 1
        return total

    print __doc__
