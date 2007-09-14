import py
from pypy.config.pypyoption import get_pypy_config
from pypy.config.config import Config

thisdir = py.magic.autopath().dirpath()

def test_required():
    conf = get_pypy_config()
    assert not conf.translating

    assert conf.objspace.usemodules.gc

    conf.objspace.std.withsmallint = True
    assert not conf.objspace.std.withprebuiltint
    conf = get_pypy_config()
    conf.objspace.std.withprebuiltint = True
    py.test.raises(ValueError, "conf.objspace.std.withsmallint = True")

def test_stacklessgc_required():
    conf = get_pypy_config()
    conf.translation.gc = "stacklessgc"
    assert conf.translation.stackless
    assert conf.translation.type_system == "lltype"

def test_check_documentation():
    from pypy.doc.config.confrest import all_optiondescrs
    configdocdir = thisdir.dirpath().dirpath().join("doc", "config")
    for descr in all_optiondescrs:
        prefix = descr._name
        c = Config(descr)
        for path in c.getpaths(include_groups=True):
            fn = prefix + "." + path + ".txt"
            assert configdocdir.join(fn).check()

def test_rweakref_required():
    conf = get_pypy_config()
    conf.translation.rweakref = False
    conf.objspace.std.allopts = True

    assert not conf.objspace.std.withtypeversion
    assert not conf.objspace.std.withmethodcache
    assert not conf.objspace.std.withshadowtracking
