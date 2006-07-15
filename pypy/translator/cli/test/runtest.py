import os
import subprocess

import py
from pypy.tool.udir import udir
from pypy.translator.translator import TranslationContext
from pypy.rpython.test.tool import BaseRtypingTest, OORtypeMixin
from pypy.rpython.lltypesystem.lltype import typeOf
from pypy.rpython.ootypesystem import ootype
from pypy.annotation.model import lltype_to_annotation

from pypy.translator.cli.option import getoption
from pypy.translator.cli.gencli import GenCli
from pypy.translator.cli.function import Function
from pypy.translator.cli.node import Node
from pypy.translator.cli.cts import CTS
from pypy.translator.cli.database import LowLevelDatabase
from pypy.translator.cli.sdk import SDK

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

def format_object(TYPE, ilasm):
    if TYPE is ootype.Void:
        ilasm.opcode('ldstr "None"')
    else:
        if isinstance(TYPE, (ootype.BuiltinType, ootype.Instance)) and TYPE is not ootype.String:
            type_ = 'object'
        else:
            type_ = cts.lltype_to_cts(TYPE)
        ilasm.call('string class [pypylib]pypy.test.Result::ToPython(%s)' % type_)


class TestEntryPoint(Node):
    """
    This class produces a 'main' method that converts its arguments
    to int32, pass them to another method and prints out the result.
    """
    
    def __init__(self, graph_to_call, wrap_exceptions=False):
        self.graph = graph_to_call
        self.db = None
        self.wrap_exceptions = wrap_exceptions

    def get_name(self):
        return 'main'

    def render(self, ilasm):
        ilasm.begin_function('main', [('string[]', 'argv')], 'void', True, 'static')

        if self.wrap_exceptions:
            ilasm.begin_try()

        # convert string arguments to their true type
        for i, arg in enumerate(self.graph.getargs()):
            ilasm.opcode('ldarg.0')
            ilasm.opcode('ldc.i4.%d' % i)
            ilasm.opcode('ldelem.ref')
            arg_type, arg_var = cts.llvar_to_cts(arg)
            ilasm.call('%s class [mscorlib]System.Convert::%s(string)' %
                       (arg_type, self.__convert_method(arg_type)))

        # call the function and convert the result to a string containing a valid python expression
        ilasm.call(cts.graph_to_signature(self.graph))
        TYPE = self.graph.getreturnvar().concretetype
        format_object(TYPE, ilasm)
        ilasm.call('void class [mscorlib]System.Console::WriteLine(string)')
        ilasm.leave('return')

        if self.wrap_exceptions:
            ilasm.end_try()

            for exc in ('[mscorlib]System.Exception', 'exceptions.Exception'):
                ilasm.begin_catch(exc)
                if getoption('nowrap'):
                    ilasm.opcode('throw')
                else:
                    ilasm.call('string class [pypylib]pypy.test.Result::FormatException(object)')
                    ilasm.call('void class [mscorlib]System.Console::WriteLine(string)')        
                    ilasm.leave('return')
                ilasm.end_catch()

        ilasm.label('return')
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
            'float64': 'ToDouble',
            'char': 'ToChar',
            }

        try:
            return _conv[arg_type]
        except KeyError:
            assert False, 'Input type %s not supported' % arg_type


def compile_function(func, annotation=[], graph=None):
    gen = _build_gen(func, annotation, graph)
    gen.generate_source()
    exe_name = gen.build_exe()
    return CliFunctionWrapper(exe_name)

def _build_gen(func, annotation, graph=None):
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
        ann = t.buildannotator()
        ann.build_types(func, annotation)

    # quick hack: force exceptions.Exception to be rendered
    def raiseValueError():
        raise ValueError
    ann.build_types(raiseValueError, [])

    t.buildrtyper(type_system="ootype").specialize()
    main_graph = t.graphs[0]

    # XXX: horrible hack :-(
    for graph in t.graphs:
        if graph.name == 'raiseValueError':
            raiseValueError_graph = graph

    if getoption('view'):
       t.view()

    if getoption('wd'):
        tmpdir = py.path.local('.')
    else:
        tmpdir = udir

    return GenCli(tmpdir, t, TestEntryPoint(main_graph, True),
                  pending_graphs=[raiseValueError_graph])

class CliFunctionWrapper(object):
    def __init__(self, exe_name):
        self._exe = exe_name

    def __call__(self, *args):
        if self._exe is None:
            py.test.skip("Compilation disabled")

        if getoption('norun'):
            py.test.skip("Execution disabled")

        arglist = SDK.runtime() + [self._exe] + map(str, args)
        env = os.environ.copy()
        env['LANG'] = 'C'
        mono = subprocess.Popen(arglist, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, env=env)
        stdout, stderr = mono.communicate()
        retval = mono.wait()
        assert retval == 0, stderr

        res = eval(stdout.strip())
        if isinstance(res, tuple):
            res = StructTuple(res) # so tests can access tuple elements with .item0, .item1, etc.
        elif isinstance(res, list):
            res = OOList(res)
        return res

class StructTuple(tuple):
    def __getattr__(self, name):
        if name.startswith('item'):
            i = int(name[len('item'):])
            return self[i]
        else:
            raise AttributeError, name

class OOList(list):
    def ll_length(self):
        return len(self)

    def ll_getitem_fast(self, i):
        return self[i]

class InstanceWrapper:
    def __init__(self, class_name):
        self.class_name = class_name

class ExceptionWrapper:
    def __init__(self, class_name):
        self.class_name = class_name

    def __repr__(self):
        return 'ExceptionWrapper(%s)' % repr(self.class_name)

class CliTest(BaseRtypingTest, OORtypeMixin):
    def __init__(self):
        self._func = None
        self._ann = None
        self._cli_func = None

    def _compile(self, fn, args, ann=None):
        if ann is None:
            ann = [lltype_to_annotation(typeOf(x)) for x in args]
        if self._func is fn and self._ann == ann:
            return self._cli_func
        else:
            self._func = fn
            self._ann = ann
            self._cli_func = compile_function(fn, ann)
            return self._cli_func
    
    def interpret(self, fn, args, annotation=None):
        f = self._compile(fn, args, annotation)
        res = f(*args)
        if isinstance(res, ExceptionWrapper):
            raise res
        return res

    def interpret_raises(self, exception, fn, args):
        import exceptions # needed by eval
        try:
            self.interpret(fn, args)
        except ExceptionWrapper, ex:
            assert issubclass(eval(ex.class_name), exception)
        else:
            assert False, 'function did raise no exception at all'

    def float_eq(self, x, y):
        return round(x, FLOAT_PRECISION) == round(y, FLOAT_PRECISION)        

    def ll_to_string(self, s):
        return s

    def ll_to_list(self, l):
        return l

    def class_name(self, value):
        return value.class_name.split(".")[-1] 

    def is_of_instance_type(self, val):
        return isinstance(val, InstanceWrapper)

    def read_attr(self, obj, name):
        py.test.skip('read_attr not supported on gencli tests')
