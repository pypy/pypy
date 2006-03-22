import os
import subprocess

import py
from pypy.tool.udir import udir
from pypy.translator.translator import TranslationContext
from pypy.translator.cli import conftest
from pypy.translator.cli.gencli import GenCli
from pypy.translator.cli.function import Node
from pypy.translator.cli.cts import graph_to_signature

class TestEntryPoint(Node):
    """
    This class produces a 'main' method that converts its arguments
    to int32, pass them to another method and prints out the result.
    """
    
    def __init__(self, graph_to_call):
        self.graph = graph_to_call

    def get_name(self):
        return 'main'

    def render(self, ilasm):
        ilasm.begin_function('main', [('string[]', 'argv')], 'void', True)

        # TODO: add support for non-int32 types
        for i, arg in enumerate(self.graph.getargs()):
            ilasm.opcode('ldarg.0')
            ilasm.opcode('ldc.i4.%d' % i)
            ilasm.opcode('ldelem.ref')
            ilasm.call('int32 class [mscorlib]System.Convert::ToInt32(string)')

        ilasm.call(graph_to_signature(self.graph))
        ilasm.call('void class [mscorlib]System.Console::WriteLine(int32)')
        ilasm.opcode('ret')
        ilasm.end_function()




class compile_function:
    def __init__(self, func, annotation=[], graph=None):
        self._func = func
        self._gen = self._build_gen(func, annotation, graph)
        self._exe = self._build_exe()

    def _build_gen(self, func, annotation, graph=None):
        try: 
            func = func.im_func
        except AttributeError: 
            pass
        t = TranslationContext()
        if graph is not None:
            graph.func = func
            ann = t.buildannotator()
            inputcells = [ann.typeannotation(a) for a in annotation]
            ann.build_graph_types(graph, inputcells)
            t.graphs.insert(0, graph)
        else:
            t.buildannotator().build_types(func, annotation)
        t.buildrtyper(type_system="ootype").specialize()
        self.graph = t.graphs[0]

        if conftest.option.view:
           t.viewcg()

        if conftest.option.wd:
            tmpdir = py.path.local('.')
        else:
            tmpdir = udir

        return GenCli(tmpdir, t, TestEntryPoint(self.graph))

    def __check_helper(self, helper):
        try:
            py.path.local.sysfind(helper) # TODO: support windows
        except py.error.ENOENT:
            py.test.skip("%s is not on your path." % helper)

    def _build_exe(self):        
        tmpfile = self._gen.generate_source()
        if conftest.option.source:
            return None

        self.__check_helper("ilasm")
        retval = subprocess.call(["ilasm", tmpfile], stdout=subprocess.PIPE)
        assert retval == 0, 'ilasm failed to assemble %s' % tmpfile
        return tmpfile.replace('.il', '.exe')

    def __call__(self, *args):
        # NB: only integers arguments are supported currently
        if self._exe is None:
            py.test.skip("Compilation disabled")

        self.__check_helper("mono")
        arglist = ["mono", self._exe] + map(str, args)
        mono = subprocess.Popen(arglist, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = mono.communicate()
        retval = mono.wait()
        assert retval == 0, stderr
        return int(stdout)
