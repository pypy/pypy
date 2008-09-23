import os
import platform

import py
from py.compat import subprocess
from pypy.tool.udir import udir
from pypy.translator.translator import TranslationContext
from pypy.rpython.test.tool import BaseRtypingTest, OORtypeMixin
from pypy.rpython.lltypesystem.lltype import typeOf
from pypy.rpython.ootypesystem import ootype
from pypy.annotation.model import lltype_to_annotation
from pypy.translator.backendopt.all import backend_optimizations
from pypy.translator.backendopt.checkvirtual import check_virtual_methods
from pypy.rpython.ootypesystem import ootype

from pypy.translator.cli.option import getoption
from pypy.translator.cli.gencli import GenCli
from pypy.translator.cli.function import Function
from pypy.translator.cli.node import Node
from pypy.translator.cli.cts import CTS
from pypy.translator.cli.database import LowLevelDatabase
from pypy.translator.cli.sdk import SDK
from pypy.translator.cli.entrypoint import BaseEntryPoint
from pypy.translator.oosupport.support import patch_os, unpatch_os


def format_object(TYPE, cts, ilasm):
    if TYPE is ootype.Void:
        ilasm.opcode('ldstr "None"')
    elif TYPE in (ootype.Unicode, ootype.UniChar):
        # the CLI type for Unicode is the very same as for
        # ootype.String, so we can't rely on overloading to
        # distinguish
        type_ = cts.lltype_to_cts(TYPE)
        ilasm.call('string class [pypylib]pypy.test.Result::ToPython_unicode(%s)' % type_)
    else:
        if isinstance(TYPE, (ootype.BuiltinType, ootype.Instance, ootype.StaticMethod)) and TYPE is not ootype.String:
            type_ = 'object'
        else:
            type_ = cts.lltype_to_cts(TYPE)
        ilasm.call('string class [pypylib]pypy.test.Result::ToPython(%s)' % type_)

class TestEntryPoint(BaseEntryPoint):
    """
    This class produces a 'main' method that converts its arguments
    to int32, pass them to another method and prints out the result.
    """

    def __init__(self, graph_to_call, wrap_exceptions=False):
        self.graph = graph_to_call
        self.wrap_exceptions = wrap_exceptions

    def get_name(self):
        return 'main'

    def render(self, ilasm):
        ilasm.begin_function('main', [('string[]', 'argv')], 'void', True, 'static')

        RETURN_TYPE = self.graph.getreturnvar().concretetype
        return_type = self.cts.lltype_to_cts(RETURN_TYPE)
        if return_type != CTS.types.void:
            ilasm.locals([(return_type, 'res')])

        if self.wrap_exceptions:
            ilasm.begin_try()

        # convert string arguments to their true type
        for i, arg in enumerate(self.graph.getargs()):
            ilasm.opcode('ldarg.0')
            ilasm.opcode('ldc.i4 %d' % i)
            ilasm.opcode('ldelem.ref')
            arg_type, arg_var = self.cts.llvar_to_cts(arg)
            self.__call_convert_method(ilasm, arg_type)

        # call the function and convert the result to a string containing a valid python expression
        ilasm.call(self.cts.graph_to_signature(self.graph))
        if return_type != CTS.types.void:
            ilasm.opcode('stloc', 'res')
        if self.wrap_exceptions:
            ilasm.leave('check_etrafo_exception')
        else:
            ilasm.leave('print_result')

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

            # check for exception tranformer exceptions
            ilasm.label('check_etrafo_exception')
            if hasattr(self.db, 'exceptiontransformer'):
                ilasm.opcode('call', 'bool rpyexc_occured()')
                ilasm.opcode('brfalse', 'print_result') # no exceptions
                ilasm.opcode('call', '[mscorlib]System.Object rpyexc_fetch_value()')
                ilasm.call('string class [pypylib]pypy.test.Result::FormatException(object)')
                ilasm.call('void class [mscorlib]System.Console::WriteLine(string)')
                ilasm.opcode('br', 'return')
            else:
                ilasm.opcode('br', 'print_result')

        ilasm.label('print_result')
        if return_type != CTS.types.void:
            ilasm.opcode('ldloc', 'res')
        format_object(RETURN_TYPE, self.cts, ilasm)
        ilasm.call('void class [mscorlib]System.Console::WriteLine(string)')

        ilasm.label('return')
        ilasm.opcode('ret')
        ilasm.end_function()
        self.db.pending_function(self.graph)

    def __call_convert_method(self, ilasm, arg_type):
        if arg_type == CTS.types.float64:
            ilasm.call('float64 class [pypylib]pypy.test.Convert::ToDouble(string)')
        else:
            ilasm.call('%s class [mscorlib]System.Convert::%s(string)' %
                       (arg_type, self.__convert_method(arg_type)))

    def __convert_method(self, arg_type):
        _conv = {
            CTS.types.int32: 'ToInt32',
            CTS.types.uint32: 'ToUInt32',
            CTS.types.int64: 'ToInt64',
            CTS.types.uint64: 'ToUInt64',
            CTS.types.bool: 'ToBoolean',
            CTS.types.char: 'ToChar',
            }

        try:
            return _conv[arg_type]
        except KeyError:
            assert False, 'Input type %s not supported' % arg_type


def compile_function(func, annotation=[], graph=None, backendopt=True,
                     auto_raise_exc=False, exctrans=False,
                     annotatorpolicy=None, nowrap=False):
    olddefs = patch_os()
    gen = _build_gen(func, annotation, graph, backendopt, exctrans, annotatorpolicy, nowrap)
    gen.generate_source()
    exe_name = gen.build_exe()
    unpatch_os(olddefs) # restore original values
    return CliFunctionWrapper(exe_name, func.__name__, auto_raise_exc)

def _build_gen(func, annotation, graph=None, backendopt=True, exctrans=False,
               annotatorpolicy=None, nowrap=False):
    try: 
        func = func.im_func
    except AttributeError: 
        pass
    t = TranslationContext()
    if graph is not None:
        graph.func = func
        ann = t.buildannotator(policy=annotatorpolicy)
        inputcells = [ann.typeannotation(a) for a in annotation]
        ann.build_graph_types(graph, inputcells)
        t.graphs.insert(0, graph)
    else:
        ann = t.buildannotator(policy=annotatorpolicy)
        ann.build_types(func, annotation)

    if getoption('view'):
       t.view()

    t.buildrtyper(type_system="ootype").specialize()
    if backendopt:
        check_virtual_methods(ootype.ROOT)
        backend_optimizations(t)
    
    main_graph = t.graphs[0]

    if getoption('view'):
       t.view()

    if getoption('wd'):
        tmpdir = py.path.local('.')
    else:
        tmpdir = udir

    return GenCli(tmpdir, t, TestEntryPoint(main_graph, not nowrap), exctrans=exctrans)

class CliFunctionWrapper(object):
    def __init__(self, exe_name, name=None, auto_raise_exc=False):
        self._exe = exe_name
        self.__name__ = name or exe_name
        self.auto_raise_exc = auto_raise_exc

    def run(self, *args):
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
        return stdout, stderr, retval

    def __call__(self, *args):
        stdout, stderr, retval = self.run(*args)
        assert retval == 0, stderr
        res = eval(stdout.strip())
        if isinstance(res, tuple):
            res = StructTuple(res) # so tests can access tuple elements with .item0, .item1, etc.
        elif isinstance(res, list):
            res = OOList(res)
        elif self.auto_raise_exc and isinstance(res, ExceptionWrapper):
            excname = res.class_name
            if excname.startswith('exceptions.'):
                import exceptions
                raise eval(excname)
            else:
                raise res # probably it's a .NET exception with no RPython equivalent
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

    def _compile(self, fn, args, ann=None, backendopt=True, auto_raise_exc=False, exctrans=False):
        if ann is None:
            ann = [lltype_to_annotation(typeOf(x)) for x in args]
        if self._func is fn and self._ann == ann:
            return self._cli_func
        else:
            self._cli_func = compile_function(fn, ann, backendopt=backendopt,
                                              auto_raise_exc=auto_raise_exc,
                                              exctrans=exctrans)
            self._func = fn
            self._ann = ann
            return self._cli_func

    def _skip_win(self, reason):
        if platform.system() == 'Windows':
            py.test.skip('Windows --> %s' % reason)

    def _skip_powerpc(self, reason):
        if platform.processor() == 'powerpc':
            py.test.skip('PowerPC --> %s' % reason)

    def _skip_llinterpreter(self, reason, skipLL=True, skipOO=True):
        pass

    def _get_backendopt(self, backendopt):
        if backendopt is None:
            backendopt = getattr(self, 'backendopt', True) # enable it by default
        return backendopt
    
    def interpret(self, fn, args, annotation=None, backendopt=None, exctrans=False):
        backendopt = self._get_backendopt(backendopt)
        f = self._compile(fn, args, annotation, backendopt=backendopt, exctrans=exctrans)
        res = f(*args)
        if isinstance(res, ExceptionWrapper):
            raise res
        return res

    def interpret_raises(self, exception, fn, args, backendopt=None, exctrans=False):
        import exceptions # needed by eval
        backendopt = self._get_backendopt(backendopt)
        try:
            self.interpret(fn, args, backendopt=backendopt, exctrans=exctrans)
        except ExceptionWrapper, ex:
            assert issubclass(eval(ex.class_name), exception)
        else:
            assert False, 'function did raise no exception at all'

    float_eq = BaseRtypingTest.float_eq_approx

    def is_of_type(self, x, type_):
        return True # we can't really test the type

    def ll_to_string(self, s):
        return s

    def ll_to_unicode(self, s):
        return s

    def ll_to_list(self, l):
        return l

    def ll_to_tuple(self, t):
        return t

    def class_name(self, value):
        return value.class_name.split(".")[-1] 

    def is_of_instance_type(self, val):
        return isinstance(val, InstanceWrapper)

    def read_attr(self, obj, name):
        py.test.skip('read_attr not supported on gencli tests')
