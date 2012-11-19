# Collects and executes application-level tests.
#
# Classes which names start with "AppTest", or function which names
# start with "app_test*" are not executed by the host Python, but
# by an interpreted pypy object space.
#
# ...unless the -A option ('runappdirect') is passed.

import py
import sys, textwrap, types
from pypy.interpreter.gateway import app2interp_temp
from pypy.interpreter.error import OperationError
from pypy.interpreter.function import Method
from pypy.tool import runsubprocess
from pypy.tool.pytest import appsupport
from pypy.tool.pytest.objspace import gettestobjspace
from pypy.tool.udir import udir
from pypy.conftest import PyPyClassCollector
from inspect import getmro


class AppError(Exception):
    def __init__(self, excinfo):
        self.excinfo = excinfo


def run_with_python(python_, target_, **definitions):
    if python_ is None:
        py.test.skip("Cannot find the default python3 interpreter to run with -A")
    # we assume that the source of target_ is in utf-8. Unfortunately, we don't
    # have any easy/standard way to determine from here the original encoding
    # of the source file
    helpers = r"""# -*- encoding: utf-8 -*-
if 1:
    import sys
    def skip(message):
        print(message)
        raise SystemExit(0)
    class ExceptionWrapper:
        pass
    def raises(exc, func, *args, **kwargs):
        try:
            if isinstance(func, str):
                if func.startswith(" ") or func.startswith("\n"):
                    # it's probably an indented block, so we prefix if True:
                    # to avoid SyntaxError
                    func = "if True:\n" + func
                frame = sys._getframe(1)
                exec(func, frame.f_globals, frame.f_locals)
            else:
                func(*args, **kwargs)
        except exc as e:
            res = ExceptionWrapper()
            res.value = e
            return res
        else:
            raise AssertionError("DID NOT RAISE")
    class Test:
        pass
    self = Test()
"""
    defs = []
    for symbol, value in definitions.items():
        if isinstance(value, tuple) and isinstance(value[0], py.code.Source):
            code, args = value
            defs.append(str(code))
            args = ','.join(repr(arg) for arg in args)
            defs.append("self.%s = anonymous(%s)\n" % (symbol, args))
        elif isinstance(value, types.MethodType):
            # "def w_method(self)"
            code = py.code.Code(value)
            defs.append(str(code.source()))
            defs.append("type(self).%s = w_%s\n" % (symbol, symbol))
        elif isinstance(value, types.ModuleType):
            name = value.__name__
            defs.append("import %s; self.%s = %s\n" % (name, symbol, name))
        elif isinstance(value, (int, str)):
            defs.append("self.%s = %r\n" % (symbol, value))
    source = py.code.Source(target_)[1:].deindent()
    pyfile = udir.join('src.py')
    source = helpers + '\n'.join(defs) + str(source)
    with pyfile.open('w') as f:
        f.write(source)
    res, stdout, stderr = runsubprocess.run_subprocess(
        python_, [str(pyfile)])
    print source
    print >> sys.stdout, stdout
    print >> sys.stderr, stderr
    if res > 0:
        raise AssertionError("Subprocess failed")


def extract_docstring_if_empty_function(fn):
    def empty_func():
        ""
        pass
    empty_func_code = empty_func.func_code
    fn_code = fn.func_code
    if fn_code.co_code == empty_func_code.co_code and fn.__doc__ is not None:
        fnargs = py.std.inspect.getargs(fn_code).args
        head = '%s(%s):' % (fn.func_name, ', '.join(fnargs))
        body = py.code.Source(fn.__doc__)
        return head + str(body.indent())
    else:
        return fn


class AppTestFunction(py.test.collect.Function):
    def __init__(self, *args, **kwargs):
        super(AppTestFunction, self).__init__(*args, **kwargs)
        self.keywords['applevel'] = True

    def _prunetraceback(self, traceback):
        return traceback

    def execute_appex(self, space, target, *args):
        try:
            target(*args)
        except OperationError, e:
            tb = sys.exc_info()[2]
            if e.match(space, space.w_KeyboardInterrupt):
                raise KeyboardInterrupt, KeyboardInterrupt(), tb
            appexcinfo = appsupport.AppExceptionInfo(space, e)
            if appexcinfo.traceback:
                raise AppError, AppError(appexcinfo), tb
            raise

    def runtest(self):
        target = self.obj
        src = extract_docstring_if_empty_function(target)
        if self.config.option.runappdirect:
            return run_with_python(self.config.option.python, src)
        space = gettestobjspace()
        filename = self._getdynfilename(target)
        func = app2interp_temp(src, filename=filename)
        print "executing", func
        self.execute_appex(space, func, space)

    def repr_failure(self, excinfo):
        if excinfo.errisinstance(AppError):
            excinfo = excinfo.value.excinfo
        return super(AppTestFunction, self).repr_failure(excinfo)

    def _getdynfilename(self, func):
        code = getattr(func, 'im_func', func).func_code
        return "[%s:%s]" % (code.co_filename, code.co_firstlineno)


class AppTestMethod(AppTestFunction):
    def setup(self):
        super(AppTestMethod, self).setup()
        instance = self.parent.obj
        w_instance = self.parent.w_instance
        space = instance.space
        for name in dir(instance):
            if name.startswith('w_'):
                if self.config.option.runappdirect:
                    setattr(instance, name[2:], getattr(instance, name))
                else:
                    obj = getattr(instance, name)
                    if isinstance(obj, types.MethodType):
                        source = py.std.inspect.getsource(obj).lstrip()
                        w_func = space.appexec([], textwrap.dedent("""
                        ():
                            %s
                            return %s
                        """) % (source, name))
                        w_obj = Method(space, w_func, w_instance)
                    else:
                        w_obj = obj
                    space.setattr(w_instance, space.wrap(name[2:]), w_obj)

    def runtest(self):
        target = self.obj
        src = extract_docstring_if_empty_function(target.im_func)
        space = target.im_self.space
        if self.config.option.runappdirect:
            appexec_definitions = self.parent.obj.__dict__
            return run_with_python(self.config.option.python, src,
                                   **appexec_definitions)
        filename = self._getdynfilename(target)
        func = app2interp_temp(src, filename=filename)
        w_instance = self.parent.w_instance
        self.execute_appex(space, func, space, w_instance)


class AppClassInstance(py.test.collect.Instance):
    Function = AppTestMethod

    def setup(self):
        super(AppClassInstance, self).setup()
        instance = self.obj
        space = instance.space
        w_class = self.parent.w_class
        if self.config.option.runappdirect:
            self.w_instance = instance
        else:
            self.w_instance = space.call_function(w_class)


class AppClassCollector(PyPyClassCollector):
    Instance = AppClassInstance

    def _haskeyword(self, keyword):
        return keyword == 'applevel' or \
               super(AppClassCollector, self)._haskeyword(keyword)

    def _keywords(self):
        return super(AppClassCollector, self)._keywords() + ['applevel']

    def setup(self):
        super(AppClassCollector, self).setup()
        cls = self.obj
        #
        # <hack>
        for name in dir(cls):
            if name.startswith('test_'):
                func = getattr(cls, name, None)
                code = getattr(func, 'func_code', None)
                if code and code.co_flags & 32:
                    raise AssertionError("unsupported: %r is a generator "
                                         "app-level test method" % (name,))
        # </hack>
        #
        space = cls.space
        clsname = cls.__name__
        if self.config.option.runappdirect:
            w_class = cls
        else:
            w_class = space.call_function(space.w_type,
                                          space.wrap(clsname),
                                          space.newtuple([]),
                                          space.newdict())
        self.w_class = w_class

