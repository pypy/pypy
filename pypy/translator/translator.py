"""PyPy Translator Frontend

Glue script putting together the various pieces of the translator.
Can be used for interactive testing of the translator. Run as:

    python -i translator.py

Example:

    t = Translator(func)
    t.view()                           # control flow graph

    print t.source()                   # original source
    print t.pyrex()                    # pyrex translation
    print t.cl()                       # common lisp translation

    t.simplify()                       # flow graph simplification
    a = t.annotate([int])              # pass the list of args types
    a.simplify()                       # simplification by annotator
    t.view()                           # graph + annotations under the mouse

    t.call(arg)                        # call original function
    t.dis()                            # bytecode disassemble

    f = t.compile()                    # pyrex compilation
    assert f(arg) == t.call(arg)       # sanity check

Some functions are provided for the benefit of interactive testing.
Try dir(test) for list of current snippets.
"""

import autopath, os

from pypy.objspace.flow.model import *
from pypy.annotation.model import *
from pypy.translator.annrpython import RPythonAnnotator
from pypy.translator.simplify import simplify_graph
from pypy.translator.genpyrex import GenPyrex
from pypy.translator.gencl import GenCL
from pypy.translator.genc.genc import GenC
from pypy.translator.gensupp import uniquemodulename
from pypy.translator.tool.buildpyxmodule import make_module_from_pyxstring
from pypy.translator.tool.buildpyxmodule import make_module_from_c
from pypy.objspace.flow import FlowObjSpace


class Translator:

    def __init__(self, func=None, verbose=False, simplifying=True,
                 builtins_can_raise_exceptions=False,
                 do_imports_immediately=True):
        self.entrypoint = func
        self.verbose = verbose
        self.simplifying = simplifying
        self.builtins_can_raise_exceptions = builtins_can_raise_exceptions
        self.do_imports_immediately = do_imports_immediately
        self.clear()

    def clear(self):
        """Clear all annotations and all flow graphs."""
        self.annotator = None
        self.flowgraphs = {}  # {function: graph}
        self.functions = []   # the keys of self.flowgraphs, in creation order
        self.callgraph = {}   # {opaque_tag: (caller, callee)}
        self.frozen = False   # when frozen, no more flowgraphs can be generated
        self.concretetypes = {}  # see getconcretetype()
        if self.entrypoint:
            self.getflowgraph()

    def getflowgraph(self, func=None, called_by=None, call_tag=None):
        """Get the flow graph for a function (default: the entry point)."""
        func = func or self.entrypoint
        try:
            graph = self.flowgraphs[func]
        except KeyError:
            if self.verbose:
                print 'getflowgraph (%s:%d) %s' % (
                    func.func_globals.get('__name__', '?'),
                    func.func_code.co_firstlineno,
                    func.__name__)
            assert not self.frozen
            space = FlowObjSpace()
            space.builtins_can_raise_exceptions = self.builtins_can_raise_exceptions
            space.do_imports_immediately = self.do_imports_immediately
            graph = space.build_flow(func)
            if self.simplifying:
                simplify_graph(graph)
            self.flowgraphs[func] = graph
            self.functions.append(func)
            try:
                import inspect
                graph.func = func
                graph.source = inspect.getsource(func)
            except IOError:
                pass  # e.g. when func is defined interactively
        if called_by:
            self.callgraph[called_by, func, call_tag] = called_by, func
        return graph

    def gv(self, func=None):
        """Shows the control flow graph for a function (default: all)
        -- requires 'dot' and 'gv'."""
        import os
        from pypy.translator.tool.make_dot import make_dot, make_dot_graphs
        if func is None:
            # show the graph of *all* functions at the same time
            graphs = []
            for func in self.functions:
                graph = self.getflowgraph(func)
                graphs.append((graph.name, graph))
            dest = make_dot_graphs(self.entrypoint.__name__, graphs)
        else:
            graph = self.getflowgraph(func)
            dest = make_dot(graph.name, graph)
        os.system('gv %s' % str(dest))

    def view(self, *functions):
        """Shows the control flow graph with annotations if computed.
        Requires 'dot' and pygame."""
        from pypy.translator.tool.graphpage import FlowGraphPage
        FlowGraphPage(self).display()

    def simplify(self, func=None):
        """Simplifies the control flow graph (default: for all functions)."""
        if func is None:
            for func in self.flowgraphs.keys():
                self.simplify(func)
        else:
            graph = self.getflowgraph(func)
            simplify_graph(graph)

    def annotate(self, input_args_types, func=None, overrides={}):
        """annotate(self, input_arg_types[, func]) -> Annotator

        Provides type information of arguments. Returns annotator.
        """
        func = func or self.entrypoint
        if self.annotator is None:
            self.annotator = RPythonAnnotator(self, overrides=overrides)
        graph = self.getflowgraph(func)
        self.annotator.build_types(graph, input_args_types, func)
        return self.annotator

    def checkgraphs(self):
        for graph in self.flowgraphs.itervalues():
            checkgraph(graph)

    def source(self, func=None):
        """Returns original Python source.
        
        Returns <interactive> for functions written while the
        interactive session.
        """
        func = func or self.entrypoint
        graph = self.getflowgraph(func)
        return getattr(graph, 'source', '<interactive>')

    def pyrex(self, input_arg_types=None, func=None):
        """pyrex(self[, input_arg_types][, func]) -> Pyrex translation

        Returns Pyrex translation. If input_arg_types is provided,
        returns type annotated translation. Subsequent calls are
        not affected by this.
        """
        return self.generatecode(GenPyrex, input_arg_types, func)

    def cl(self, input_arg_types=None, func=None):
        """cl(self[, input_arg_types][, func]) -> Common Lisp translation
        
        Returns Common Lisp translation. If input_arg_types is provided,
        returns type annotated translation. Subsequent calls are
        not affected by this.
        """
        return self.generatecode(GenCL, input_arg_types, func)

    def c(self):
        """c(self) -> C (CPython) translation
        
        Returns C (CPython) translation.
        """
        from StringIO import StringIO 
        out = StringIO()
        genc = GenC(out, self)
        return out.getvalue()
    
    def generatecode(self, gencls, input_arg_types, func):
        if input_arg_types is None:
            ann = self.annotator
        else:
            ann = RPythonAnnotator(self)
        if func is None:
            codes = [self.generatecode1(gencls, input_arg_types,
                                        self.entrypoint, ann)]
            for func in self.functions:
                if func is not self.entrypoint:
                    code = self.generatecode1(gencls, None, func, ann,
                                              public=False)
                    codes.append(code)
        else:
            codes = [self.generatecode1(gencls, input_arg_types, func, ann)]
        code = self.generateglobaldecl(gencls, func, ann)
        if code:
            codes.insert(0, code)
        return '\n\n#_________________\n\n'.join(codes)

    def generatecode1(self, gencls, input_arg_types, func, ann, public=True):
        graph = self.getflowgraph(func)
        g = gencls(graph)
        g.by_the_way_the_function_was = func   # XXX
        if input_arg_types is not None:
            ann.build_types(graph, input_arg_types, func)
        if ann is not None:
            g.setannotator(ann)
        return g.emitcode(public)

    def generateglobaldecl(self, gencls, func, ann):
        graph = self.getflowgraph(func)
        g = gencls(graph)
        if ann is not None:
            g.setannotator(ann)
        return g.globaldeclarations()

    def compile(self):
        """Returns compiled function, compiled using Pyrex.
        """
        from pypy.tool.udir import udir
        name = self.entrypoint.func_name
        pyxcode = self.pyrex()
        mod = make_module_from_pyxstring(name, udir, pyxcode)
        return getattr(mod, name)

    def ccompile(self, really_compile=True):
        """Returns compiled function, compiled using the C generator.
        """
        from pypy.tool.udir import udir
        name = uniquemodulename(self.entrypoint.func_name)
        cfile = udir.join('%s.c' % name)
        f = cfile.open('w')
        f2 = udir.join('%s-init.py' % name).open('w+')
        GenC(f, self, name, f2=f2)
        f2.close()
        f.close()
        if not really_compile:
            return cfile
        mod = make_module_from_c(cfile,
            include_dirs=[os.path.join(autopath.this_dir, 'genc')])
        return getattr(mod, self.entrypoint.func_name)

    def call(self, *args):
        """Calls underlying Python function."""
        return self.entrypoint(*args)

    def dis(self, func=None):
        """Disassembles underlying Python function to bytecodes."""
        from dis import dis
        dis(func or self.entrypoint)

##    def consider_call(self, ann, func, args):
##        graph = self.getflowgraph(func)
##        ann.addpendingblock(graph.startblock, args)
##        result_var = graph.getreturnvar()
##        try:
##            return ann.binding(result_var)
##        except KeyError:
##            # typical case for the 1st call, because addpendingblock() did
##            # not actually start the analysis of the called function yet.
##            return impossiblevalue

    def getconcretetype(self, cls, *args):
        # Return a (cached) 'concrete type' object attached to this translator.
        # Concrete types are what is put in the 'concretetype' attribute of
        # the Variables and Constants of the flow graphs by typer.py to guide
        # the code generators.
        try:
            return self.concretetypes[cls, args]
        except KeyError:
            result = self.concretetypes[cls, args] = cls(self, *args)
            return result


if __name__ == '__main__':
    from pypy.translator.test import snippet as test
    print __doc__

    # 2.3 specific -- sanxiyn
    import os
    os.putenv("PYTHONINSPECT", "1")
