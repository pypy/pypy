import py
from pypy.config.pypyoption import get_pypy_config, set_pypy_opt_level
from pypy.config.config import Config, ConfigError
from pypy.config.translationoption import set_opt_level

thisdir = py.path.local(__file__).dirpath()

def test_required():
    conf = get_pypy_config()
    assert not conf.translating

    assert conf.objspace.usemodules.gc

    conf.objspace.std.withsmallint = True
    assert not conf.objspace.std.withprebuiltint
    conf = get_pypy_config()
    conf.objspace.std.withprebuiltint = True
    py.test.raises(ConfigError, "conf.objspace.std.withsmallint = True")

def test_conflicting_gcrootfinder():
    conf = get_pypy_config()
    conf.translation.gc = "boehm"
    py.test.raises(ConfigError, "conf.translation.gcrootfinder = 'asmgcc'")


def test_frameworkgc():
    for name in ["marksweep", "semispace"]:
        conf = get_pypy_config()
        assert conf.translation.gctransformer != "framework"
        conf.translation.gc = name
        assert conf.translation.gctransformer == "framework"

def test_set_opt_level():
    conf = get_pypy_config()
    set_opt_level(conf, '0')
    assert conf.translation.gc == 'boehm'
    assert conf.translation.backendopt.none == True
    conf = get_pypy_config()
    set_opt_level(conf, '2')
    assert conf.translation.gc != 'boehm'
    assert not conf.translation.backendopt.none
    conf = get_pypy_config()
    set_opt_level(conf, 'mem')
    assert conf.translation.gcremovetypeptr
    assert not conf.translation.backendopt.none

def test_set_pypy_opt_level():
    conf = get_pypy_config()
    set_pypy_opt_level(conf, '2')
    assert conf.objspace.std.newshortcut
    conf = get_pypy_config()
    set_pypy_opt_level(conf, '0')
    assert not conf.objspace.std.newshortcut

def test_rweakref_required():
    conf = get_pypy_config()
    conf.translation.rweakref = False
    set_pypy_opt_level(conf, '3')

    assert not conf.objspace.std.withtypeversion
    assert not conf.objspace.std.withmethodcache

def test_check_documentation():
    def check_file_exists(fn):
        assert configdocdir.join(fn).check()

    from pypy.doc.config.confrest import all_optiondescrs
    configdocdir = thisdir.dirpath().dirpath().join("doc", "config")
    for descr in all_optiondescrs:
        prefix = descr._name
        c = Config(descr)
        for path in c.getpaths(include_groups=True):
            fn = prefix + "." + path + ".txt"
            yield check_file_exists, fn

def test__ffi_opt():
    config = get_pypy_config(translating=True)
    config.objspace.usemodules._ffi = True
    assert config.translation.jit_ffi
