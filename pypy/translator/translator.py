"""PyPy Translator Frontend

Glue script putting together the various pieces of the translator.
Can be used for interactive testing of the translator. Run as:

    python -i translator.py

Example:

    t = Translator(func)
    t.gv()                             # control flow graph

    print t.source()                   # original source
    print t.pyrex()                    # pyrex translation
    print t.cl()                       # common lisp translation

    t.simplify()                       # flow graph simplification
    a = t.annotate([int])              # pass the list of args types
    a.simplify()                       # simplification by annotator

    f = t.compile()                    # pyrex compilation
    assert f(arg) == func(arg)

Some functions will be provided for the benefit of interactive testing.
Currently there are my_bool and my_range.
"""

import autopath

from pypy.objspace.flow.model import *
from pypy.translator.annset import AnnotationSet, Cell
from pypy.translator.annotation import Annotator
from pypy.translator.simplify import simplify_graph
from pypy.translator.genpyrex import GenPyrex
from pypy.translator.gencl import GenCL
from pypy.translator.tool.buildpyxmodule import make_module_from_pyxstring
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
            self.py_source = inspect.getsource(func)
        except IOError:
            # e.g. when func is defined interactively
            self.py_source = "<interactive>"

    def gv(self):
        """Shows the control flow graph -- requires 'dot' and 'gv'."""
        import os
        from pypy.translator.tool.make_dot import make_dot
        from pypy.tool.udir import udir
        dest = make_dot(self.flowgraph, udir, 'ps')
        os.system('gv %s' % str(dest))

    def simplify(self):
        """Simplifies the control flow graph."""
        self.flowgraph = simplify_graph(self.flowgraph)

    def annotate(self, input_args_types):
        """annotate(self, input_arg_types) -> Annotator

        Provides type information of arguments. Returns annotator.
        """
        self.annotator = Annotator(self.flowgraph)
        self.annotator.build_types(input_args_types)
        return self.annotator

    def source(self):
        """Returns original Python source.
        
        Returns <interactive> for functions written while the
        interactive session.
        """
        return self.py_source

    def pyrex(self):
        """Returns Pyrex translation."""
        g = GenPyrex(self.flowgraph)
        if self.annotator:
            g.setannotator(self.annotator)
        return g.emitcode()

    def cl(self):
        """Returns Common Lisp translation."""
        g = GenCL(self.flowgraph)
        if self.annotator:
            g.ann = self.annotator
        return g.emitcode()

    def compile(self):
        """Returns compiled function.

        Currently function is only compiled using Pyrex.
        """
        from pypy.tool.udir import udir
        name = self.entrypoint.func_name
        pyxcode = self.pyrex()
        mod = make_module_from_pyxstring(name, udir, pyxcode)
        return getattr(mod, name)


if __name__ == '__main__':

    def my_bool(x):
        return not not x

    def my_range(i):
        lst = []
        while i > 0:
            i = i - 1
            lst.append(i)
        lst.reverse()
        return lst

    print __doc__

    # 2.3 specific -- sanxiyn
    import os
    os.putenv("PYTHONINSPECT", "1")
