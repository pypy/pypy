import os
import subprocess
import platform

import py
from pypy.tool.udir import udir
from pypy.translator.translator import TranslationContext
from pypy.translator.cli.option import getoption
from pypy.translator.cli.gencli import GenCli
from pypy.translator.cli.function import Function
from pypy.translator.cli.node import Node
from pypy.translator.cli.cts import CTS
from pypy.translator.cli.database import LowLevelDatabase

FLOAT_PRECISION = 8

cts = CTS(LowLevelDatabase()) # this is a hack!

def check(func, annotation, args):
    mono = compile_function(func, annotation)
    res1 = func(*args)
    res2 = mono(*args)

    if type(res1) is float:
        assert round(res1, FLOAT_PRECISION) == round(res2, FLOAT_PRECISION)
    else:
        assert res1 == res2

class TestEntryPoint(Node):
    """
    This class produces a 'main' method that converts its arguments
    to int32, pass them to another method and prints out the result.
    """
    
    def __init__(self, graph_to_call):
        self.graph = graph_to_call
        self.db = None

    def get_name(self):
        return 'main'

    def render(self, ilasm):
        ilasm.begin_function('main', [('string[]', 'argv')], 'void', True, 'static')

        # TODO: only int32 and bool are tested
        for i, arg in enumerate(self.graph.getargs()):
            ilasm.opcode('ldarg.0')
            ilasm.opcode('ldc.i4.%d' % i)
            ilasm.opcode('ldelem.ref')
            arg_type, arg_var = cts.llvar_to_cts(arg)
            ilasm.call('%s class [mscorlib]System.Convert::%s(string)' %
                       (arg_type, self.__convert_method(arg_type)))

        ilasm.call(cts.graph_to_signature(self.graph))

        # print the result using the appropriate WriteLine overload
        ret_type, ret_var = cts.llvar_to_cts(self.graph.getreturnvar())
        ilasm.call('void class [mscorlib]System.Console::WriteLine(%s)' % ret_type)
        ilasm.opcode('ret')
        ilasm.end_function()
        self.db.pending_function(self.graph)

    def __convert_method(self, arg_type):
        _conv = {
            'int32': 'ToInt32',
            'unsigned int32': 'ToUInt32',
            'int64': 'ToInt64',
            'unsigned int64': 'ToUInt64',
            'bool': 'ToBoolean',
            'float64': 'ToDouble'
            }

        try:
            return _conv[arg_type]
        except KeyError:
            assert False, 'Input type %s not supported' % arg_type


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

        if getoption('view'):
           t.viewcg()

        if getoption('wd'):
            tmpdir = py.path.local('.')
        else:
            tmpdir = udir

        return GenCli(tmpdir, t, TestEntryPoint(self.graph))

    def __check_helper(self, helper):
        try:
            py.path.local.sysfind(helper)
        except py.error.ENOENT:
            py.test.skip("%s is not on your path." % helper)

    def __get_runtime(self):
        if platform.system() == 'Windows':
            return []
        else:
            self.__check_helper('mono')
            return ['mono']

    def _build_exe(self):        
        tmpfile = self._gen.generate_source()
        if getoption('source'):
            return None

        self.__check_helper("ilasm")
        ilasm = subprocess.Popen(["ilasm", tmpfile], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = ilasm.communicate()
        retval = ilasm.wait()
        assert retval == 0, 'ilasm failed to assemble %s (%s):\n%s' % (self.graph.name, tmpfile, stdout)
        return tmpfile.replace('.il', '.exe')

    def __call__(self, *args):
        if self._exe is None:
            py.test.skip("Compilation disabled")

        runtime = self.__get_runtime()
        arglist = runtime + [self._exe] + map(str, args)
        mono = subprocess.Popen(arglist, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = mono.communicate()
        retval = mono.wait()
        assert retval == 0, stderr

        ret_type, ret_var = cts.llvar_to_cts(self.graph.getreturnvar())
        if 'int' in ret_type:
            return int(stdout)
        elif ret_type == 'float64':
            return float(stdout)
        elif ret_type == 'bool':
            return stdout.strip().lower() == 'true'
        else:
            assert False, 'Return type %s is not supported' % ret_type
