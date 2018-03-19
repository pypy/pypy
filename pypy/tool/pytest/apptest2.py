import sys

import pytest
import pypy.interpreter.function
from pypy.interpreter.error import OperationError
from pypy.tool.pytest import objspace
from pypy.tool.pytest import appsupport


class AppTestModule(pytest.Module):

    def collect(self):
        space = objspace.gettestobjspace()
        w_mod = space.appexec([] ,"""():
        import sys
        sys.path.insert(0, '%s')
        import _pytest.assertion.rewrite, py.path

        stat, co = _pytest.assertion.rewrite._rewrite_test(None, py.path.local('%s'))
        mod = _pytest.assertion.rewrite.create_module(co)
        return mod
        """ % (self.config.rootdir, str(self.fspath)))
        mod_dict = w_mod.getdict(space).unwrap(space)
        items = []
        for name, w_obj in mod_dict.items():
            if not name.startswith('test_'):
                continue
            if not isinstance(w_obj, pypy.interpreter.function.Function):
                continue
            items.append(AppTestFunction(name, self, w_obj))
        return items

    def setup(self):
        pass


class AppError(Exception):

    def __init__(self, excinfo):
        self.excinfo = excinfo


class AppTestFunction(pytest.Item):

    def __init__(self, name, parent, w_obj):
        super(AppTestFunction, self).__init__(name, parent)
        self.w_obj = w_obj

    def runtest(self):
        target = self.w_obj
        space = target.space
        self.execute_appex(space, target)

    def repr_failure(self, excinfo):
        if excinfo.errisinstance(AppError):
            excinfo = excinfo.value.excinfo
        return super(AppTestFunction, self).repr_failure(excinfo)

    def execute_appex(self, space, w_func):
        space.getexecutioncontext().set_sys_exc_info(None)
        try:
            space.call_function(w_func)
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
