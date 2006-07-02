"""
All code for using LLVM's JIT in one place
"""

import py
from pypy.translator.translator import TranslationContext
from pypy.translator.llvm.database import Database
from pypy.translator.llvm.codewriter import CodeWriter
from pypy.translator.llvm.opwriter import OpWriter
from pypy.translator.llvm.funcnode import FuncNode
from pypy.translator.llvm.gc import GcPolicy
from pypy.translator.llvm.exception import ExceptionPolicy
from pypy.translator.llvm.pyllvm import pyllvm
from cStringIO import StringIO

from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("llvm/jitcode")
py.log.setconsumer("llvm/jitcode", ansi_log)


# Custom database, codewriter and opwriter
class JITDatabase(Database): pass
class JITCodeWriter(CodeWriter): pass
class JITOpWriter(OpWriter): pass

class GraphContainer(object):   # XXX what should this really be?
    def __init__(self, graph):
        self.graph = graph

# LLVM execution engine (llvm module) that is going to contain the code
ee = pyllvm.ExecutionEngine()


# Create a LLVM 'execution engine' which wraps the LLVM JIT
class JITcode(object):

    def __init__(self, typer):
        self.typer = typer
        self.db = JITDatabase(genllvm=None, translator=None) #XXX fake
        self.db.gcpolicy = GcPolicy.new(self.db,'raw')
        self.db.exceptionpolicy = ExceptionPolicy.new(self.db, 'explicit')
        self.code = StringIO()
        self.codewriter = JITCodeWriter(self.code, self.db)
        self.codewriter.linkage = '' #XXX default linkage is internal which does not work here
        self.opwriter = JITOpWriter(self.db, self.codewriter)
        self.graph_ref = {} #name by which LLVM knowns a graph

    def backendoptimizations(self, graph, translator=None):
        from pypy.translator.backendopt.removenoops import remove_same_as
        from pypy.translator import simplify
        from pypy.translator.unsimplify import remove_double_links
        remove_same_as(graph)
        simplify.eliminate_empty_blocks(graph)
        simplify.transform_dead_op_vars(graph, translator)
        remove_double_links(None, graph)
        #translator.checkgraph(graph)

    def codegen(self, graph):
        self.backendoptimizations(graph)
        node = FuncNode(self.db, GraphContainer(graph))
        node.writeimpl(self.codewriter)
        log('code =' + self.code.getvalue())
        ee.parse(self.code.getvalue())
        return node.ref[1:] #strip of % prefix

    def eval_graph(self, graph, args=()):
        """
        From a graph this generates llvm code that gets parsed.
        It would be faster and use less memory to generate the code
        without first generating the entire graph.
        It would also be faster (probably) to extend pyllvm so blocks/instructions/etc.
        could be added directly instead of using intermediate llvm sourcecode.
        """
        log('eval_graph: %s(%s)' % (graph.name, args))
        if graph not in self.graph_ref:
            self.graph_ref[graph] = self.codegen(graph)
        llvmfunc = ee.getModule().getNamedFunction(self.graph_ref[graph])
        return llvmfunc(*args)
