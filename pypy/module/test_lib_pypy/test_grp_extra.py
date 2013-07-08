from __future__ import absolute_import
import py
try:
    from lib_pypy import grp
except ImportError:
    py.test.skip("No grp module on this platform")

def test_basic():
    g = grp.getgrnam("root")
    assert g.gr_gid == 0
    assert g.gr_mem == ['root'] or g.gr_mem == []
    assert g.gr_name == 'root'
    assert isinstance(g.gr_passwd, str)    # usually just 'x', don't hope :-)

def test_extra():
    py.test.raises(TypeError, grp.getgrnam, False)
    py.test.raises(TypeError, grp.getgrnam, None)

def test_struct_group():
    g = grp.struct_group((10, 20, 30, 40))
    assert len(g) == 4
    assert list(g) == [10, 20, 30, 40]
    assert g.gr_name == 10
    assert g.gr_passwd == 20
    assert g.gr_gid == 30
    assert g.gr_mem == 40
