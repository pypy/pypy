import py
from pypy.config.pypyoption import pypy_optiondescription
from pypy.config.config import Config

def test_required():
    conf = Config(pypy_optiondescription)
    assert not conf.translating

    assert conf.objspace.usemodules.gc

    conf.objspace.std.withsmallint = True
    assert not conf.objspace.std.withprebuiltint
    conf = Config(pypy_optiondescription)
    conf.objspace.std.withprebuiltint = True
    py.test.raises(ValueError, "conf.objspace.std.withsmallint = True")

def test_objspace_incopatibilities():
    conf = Config(pypy_optiondescription)
    conf.objspace.name = "logic"
    assert not conf.objspace.geninterp

def test_stacklessgc_required():
    conf = Config(pypy_optiondescription)
    conf.translation.gc = "stacklessgc"
    assert conf.translation.stackless
    assert conf.translation.type_system == "lltype"
