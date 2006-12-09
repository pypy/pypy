import py
from pypy.config.pypyoption import get_pypy_config

def test_required():
    conf = get_pypy_config()
    assert not conf.translating

    assert conf.objspace.usemodules.gc

    conf.objspace.std.withsmallint = True
    assert not conf.objspace.std.withprebuiltint
    conf = get_pypy_config()
    conf.objspace.std.withprebuiltint = True
    py.test.raises(ValueError, "conf.objspace.std.withsmallint = True")

def test_objspace_incopatibilities():
    conf = get_pypy_config()
    conf.objspace.name = "logic"
    assert not conf.objspace.geninterp

def test_stacklessgc_required():
    conf = get_pypy_config()
    conf.translation.gc = "stacklessgc"
    assert conf.translation.stackless
    assert conf.translation.type_system == "lltype"
