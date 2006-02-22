"""PyPy Translator Frontend

The Translator is a glue class putting together the various pieces of the
translation-related code.  It can be used for interactive testing of the
translator; see pypy/bin/translator.py.
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
        'import_hints': {},
        }

    def __init__(self, **flowing_flags):
        self.flags = copy.deepcopy(self.FLOWING_FLAGS)
        self.flags.update(flowing_flags)
        if len(self.flags) > len(self.FLOWING_FLAGS):
            raise TypeError("unexpected keyword argument")
        self.annotator = None
        self.rtyper = None
        self.graphs = []      # [graph]
        self.callgraph = {}   # {opaque_tag: (caller-graph, callee-graph)}
        self._prebuilt_graphs = {}   # only used by the pygame viewer

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

# _______________________________________________________________

class Translator(TranslationContext):

    def __init__(self, func, **flowing_flags):
        super(Translator, self).__init__(**flowing_flags)
        self.entrypoint = func

    def __getstate__(self):
        # try to produce things a bit more ordered
        XXX
        return self.entrypoint, self.functions, self.__dict__

    def __setstate__(self, args):
        XXX
        assert len(args) == 3
        self.__dict__.update(args[2])
        assert args[0] is self.entrypoint and args[1] is self.functions

    def gv(self):
        """Shows the control flow graph -- requires 'dot' and 'gv'."""
        import os
        from pypy.translator.tool.make_dot import make_dot, make_dot_graphs
        graphs = []
        for graph in self.graphs:
            graphs.append((graph.name, graph))
        dest = make_dot_graphs(self.entrypoint.__name__, graphs)
        os.system('gv %s' % str(dest))

    def simplify(self, passes=True):
        """Simplifies all the control flow graphs."""
        for graph in self.graphs:
            simplify_graph(graph, passes)
            
    def annotate(self, input_args_types, policy=None):
        """annotate(self, input_arg_types) -> Annotator

        Provides type information of arguments. Returns annotator.
        """
        annotator = self.buildannotator(policy)
        annotator.build_types(self.entrypoint, input_args_types)
        return annotator

    def specialize(self, **flags):
        rtyper = self.buildrtyper(
            type_system=flags.pop("type_system", "lltype"))
        rtyper.specialize(**flags)

    def backend_optimizations(self, **kwds):
        from pypy.translator.backendopt.all import backend_optimizations
        backend_optimizations(self, **kwds)

    def source(self):
        """Returns original Python source.
        
        Returns <interactive> for functions written during the
        interactive session.
        """
        FIX_ME
        return self.entrypointgraph.source

    def pyrex(self, input_arg_types=None, func=None):
        """pyrex(self[, input_arg_types][, func]) -> Pyrex translation

        Returns Pyrex translation. If input_arg_types is provided,
        returns type annotated translation. Subsequent calls are
        not affected by this.
        """
        FIX_ME
        from pypy.translator.pyrex.genpyrex import GenPyrex
        return self.generatecode(GenPyrex, input_arg_types, func)

    def cl(self, input_arg_types=None, func=None):
        """cl(self[, input_arg_types][, func]) -> Common Lisp translation
        
        Returns Common Lisp translation. If input_arg_types is provided,
        returns type annotated translation. Subsequent calls are
        not affected by this.
        """
        FIX_ME
        from pypy.translator.gencl import GenCL
        return self.generatecode(GenCL, input_arg_types, func)

    def c(self):
        """c(self) -> C (CPython) translation
        
        Returns C (CPython) translation.
        """
        FIX_ME
        from pypy.translator.c import genc
        from cStringIO import StringIO
        f = StringIO()
        database, ignored = genc.translator2database(self)
        genc.gen_readable_parts_of_main_c_file(f, database)
        return f.getvalue()

    def llvm(self):
        """llvm(self) -> LLVM translation
        
        Returns LLVM translation.
        """
        FIX_ME
        from pypy.translator.llvm.genllvm import GenLLVM
        if self.annotator is None:
            raise ValueError, "function has to be annotated."
        gen = GenLLVM(self)
        filename = gen.gen_llvm_source()
        f = open(str(filename), "r")
        result = f.read()
        f.close()
        return result
    
    def generatecode(self, gencls, input_arg_types, func):
        if input_arg_types is None:
            ann = self.annotator
        else:
            from pypy.annotation.annrpython import RPythonAnnotator
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

    def pyrexcompile(self):
        """Returns compiled function, compiled using Pyrex.
        """
        FIX_ME
        from pypy.translator.tool.cbuild import make_module_from_pyxstring
        from pypy.tool.udir import udir
        name = self.entrypoint.func_name
        pyxcode = self.pyrex()
        mod = make_module_from_pyxstring(name, udir, pyxcode)
        return getattr(mod, name)

    def compile(self, compiler='c', **kw):
        compiler += 'compile'
        if hasattr(self, compiler):
            compiler = getattr(self,compiler)
            return compiler(**kw)
        else:
            raise NotImplementedError, "Compiler not known", compiler
    
    def ccompile(self, really_compile=True, standalone=False, gcpolicy=None):
        """Returns compiled function (living in a new C-extension module), 
           compiled using the C generator.
        """
        FIX_ME
        cbuilder = self.cbuilder(standalone=standalone, gcpolicy=gcpolicy)
        c_source_filename = cbuilder.generate_source()
        if not really_compile: 
            return c_source_filename
        cbuilder.compile()
        if standalone:
            return cbuilder.executable_name
        cbuilder.import_module()    
        return cbuilder.get_entry_point()

    def cbuilder(self, standalone=False, gcpolicy=None, thread_enabled=False):
        FIX_ME
        from pypy.translator.c import genc
        if standalone:
            return genc.CStandaloneBuilder(self, gcpolicy=gcpolicy, thread_enabled=thread_enabled)
        else:
            return genc.CExtModuleBuilder(self, gcpolicy=gcpolicy, thread_enabled=thread_enabled)

    def llvmcompile(self, really_compile=True, standalone=False, optimize=True, exe_name=None, gcpolicy=None):
        """llvmcompile(self, really_compile=True, standalone=False, optimize=True) -> LLVM translation
        
        Returns LLVM translation with or without optimization.
        """
        FIX_ME
        from pypy.translator.llvm import genllvm
        if self.annotator is None:
            raise ValueError, "function has to be annotated."
        if standalone:
            if not exe_name:
                exe_name = self.entrypoint.__name__
        else:
            exe_name = None
        return genllvm.genllvm(self, really_compile=really_compile, standalone=standalone, optimize=optimize, exe_name=exe_name, gcpolicy=gcpolicy)

    def asmcompile(self, processor='virt'):
        FIX_ME
        from pypy.translator.asm import genasm
        assert processor in ['ppc', 'virt', 'virtfinite']
        assert self.rtyper is not None, 'must specialize'
        graph = graphof(self, self.entrypoint)
        return genasm.genasm(graph, processor)

    def call(self, *args):
        """Calls underlying Python function."""
        return self.entrypoint(*args)

    def dis(self):
        """Disassembles underlying Python function to bytecodes."""
        from dis import dis
        dis(self.entrypoint)
