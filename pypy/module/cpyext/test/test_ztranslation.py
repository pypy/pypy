from pypy.objspace.fake.checkmodule import checkmodule
from pypy.module.cpyext import pyobject

def test_cpyext_translates():
    def from_ref(space, ref):
        # XXX: avoid 'assert isinstance(w_type, W_TypeObject)' from the
        # original from_ref, just return w_some_obj
        return space.w_object
    old, pyobject.from_ref = pyobject.from_ref, from_ref
    try:
        checkmodule('cpyext', '_ffi')
    finally:
        pyobject.from_ref = old
