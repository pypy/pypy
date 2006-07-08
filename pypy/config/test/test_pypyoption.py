import py
from pypy.config.pypyoption import pypy_optiondescription
from pypy.config.config import Config

def test_required():
    conf = Config(pypy_optiondescription)
    assert not conf.translating

    conf.objspace.nofaking = True
    assert conf.objspace.uselibfile
    py.test.raises(ValueError, "conf.objspace.uselibfile = False")
    
    assert conf.objspace.usemodules.gc

    conf.objspace.std.withsmallint = True
    assert not conf.objspace.std.withprebuiltint
    conf.objspace.std.withprebuiltint = True
    assert not conf.objspace.std.withsmallint
