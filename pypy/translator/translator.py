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

    t.call(arg)                        # call original function
    t.dis()                            # bytecode disassemble

    f = t.compile()                    # pyrex compilation
    assert f(arg) == t.call(arg)       # sanity check

Some functions are provided for the benefit of interactive testing.
Try dir(test) for list of current snippets.
"""


import autopath

from pypy.objspace.flow.model import *
from pypy.translator.annrpython import RPythonAnnotator
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
        dest = make_dot('dummy', self.flowgraph)
        os.system('gv %s' % str(dest))

    def simplify(self):
        """Simplifies the control flow graph."""
        self.flowgraph = simplify_graph(self.flowgraph)

    def annotate(self, input_args_types):
        """annotate(self, input_arg_types) -> Annotator

        Provides type information of arguments. Returns annotator.
        """
        self.annotator = RPythonAnnotator()
        self.annotator.build_types(self.flowgraph, input_args_types)
        return self.annotator

    def source(self):
        """Returns original Python source.
        
        Returns <interactive> for functions written while the
        interactive session.
        """
        return self.py_source

    def pyrex(self, input_arg_types=None):
        """pyrex(self, [input_arg_types]) -> Pyrex translation

        Returns Pyrex translation. If input_arg_types is provided,
        returns type annotated translation. Subsequent calls are
        not affected by this.
        """
        g = GenPyrex(self.flowgraph)
        if input_arg_types is not None:
            g.annotate(input_arg_types)
        elif self.annotator:
            g.setannotator(self.annotator)
        return g.emitcode()

    def cl(self, input_arg_types=None):
        """cl(self, [input_arg_types]) -> Common Lisp translation
        
        Returns Common Lisp translation. If input_arg_types is provided,
        returns type annotated translation. Subsequent calls are
        not affected by this.
        """
        g = GenCL(self.flowgraph)
        if input_arg_types is not None:
            g.annotate(input_arg_types)
        elif self.annotator:
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

    def call(self, *args):
        """Calls underlying Python function."""
        return self.entrypoint(*args)

    def dis(self):
        """Disassembles underlying Python function to bytecodes."""
        from dis import dis
        dis(self.entrypoint)


if __name__ == '__main__':
    from pypy.translator.test import snippet as test
    print __doc__

    # 2.3 specific -- sanxiyn
    import os
    os.putenv("PYTHONINSPECT", "1")
