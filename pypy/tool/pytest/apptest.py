# Collects and executes application-level tests.
#
# Classes which names start with "AppTest", or function which names
# start with "app_test*" are not executed by the host Python, but
# by an interpreted pypy object space.
#
# ...unless the -A option ('runappdirect') is passed.

import py
import sys, textwrap, types, gc
from pypy.interpreter.gateway import app2interp_temp
from pypy.interpreter.error import OperationError
from pypy.interpreter.function import Method
from pypy.tool.pytest import appsupport
from pypy.tool.pytest.objspace import gettestobjspace
from inspect import getmro


class AppError(Exception):
    def __init__(self, excinfo):
        self.excinfo = excinfo


class AppTestFunction(py.test.collect.Function):
    def _prunetraceback(self, traceback):
        return traceback

    def execute_appex(self, space, target, *args):
        self.space = space
        try:
            target(*args)
        except OperationError as e:
            if self.config.option.raise_operr:
                raise
            tb = sys.exc_info()[2]
            if e.match(space, space.w_KeyboardInterrupt):
                raise KeyboardInterrupt, KeyboardInterrupt(), tb
            appexcinfo = appsupport.AppExceptionInfo(space, e)
            if appexcinfo.traceback:
                raise AppError, AppError(appexcinfo), tb
            raise

    def runtest(self):
        target = self.obj
        if self.config.option.runappdirect:
            return target()
        space = gettestobjspace()
        filename = self._getdynfilename(target)
        func = app2interp_temp(target, filename=filename)
        print "executing", func
        self.execute_appex(space, func, space)

    def repr_failure(self, excinfo):
        if excinfo.errisinstance(AppError):
            excinfo = excinfo.value.excinfo
        return super(AppTestFunction, self).repr_failure(excinfo)

    def _getdynfilename(self, func):
        code = getattr(func, 'im_func', func).func_code
        return "[%s:%s]" % (code.co_filename, code.co_firstlineno)

    def track_allocations_collect(self):
        gc.collect()
        # must also invoke finalizers now; UserDelAction
        # would not run at all unless invoked explicitly
        if hasattr(self, 'space'):
            self.space.getexecutioncontext()._run_finalizers_now()


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
                        w_obj = Method(space, w_func, w_instance, space.w_None)
                    else:
                        w_obj = obj
                    space.setattr(w_instance, space.wrap(name[2:]), w_obj)

    def runtest(self):
        target = self.obj
        if self.config.option.runappdirect:
            return target()
        space = target.im_self.space
        filename = self._getdynfilename(target)
        func = app2interp_temp(target.im_func, filename=filename)
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


class AppClassCollector(py.test.Class):
    Instance = AppClassInstance

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

