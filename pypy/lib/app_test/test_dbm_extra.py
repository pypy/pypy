from pypy.lib import dbm
from pypy.tool.udir import udir

def test_get():
    path = str(udir.join('test_dbm_extra.test_get'))
    d = dbm.open(path, 'c')
    x = d.get("42")
    assert x is None
    d.close()
