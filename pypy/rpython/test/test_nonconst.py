
""" Test of non-constant constant.
"""

from pypy.rpython.nonconst import NonConstant

from pypy.objspace.flow import FlowObjSpace
from pypy.annotation.annrpython import RPythonAnnotator

def test_nonconst():
    def nonconst_f():
        a = NonConstant(3)
        return a
    
    a = RPythonAnnotator()
    s = a.build_types(nonconst_f, [])
    assert s.knowntype is int
    assert not hasattr(s, 'const')
