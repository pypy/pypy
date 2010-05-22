import py
from pypy.conftest import option, gettestobjspace

def pytest_collect_directory(parent):
    if parent.config.option.runappdirect:
        py.test.skip("cannot be run by py.test -A")

    # ensure additional functions are registered
    import pypy.module.cpyext.test.test_cpyext

def pytest_funcarg__space(request):
    return gettestobjspace(usemodules=['cpyext', 'thread'])

def pytest_funcarg__api(request):
    return request.cls.api

