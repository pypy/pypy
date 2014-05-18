from pypy.objspace.fake.checkmodule import checkmodule
from pypy.module.cpyext import pyobject

def test_cpyext_translates(monkeypatch):
    def from_ref(space, ref):
        # XXX: avoid 'assert isinstance(w_type, W_TypeObject)' from the
        # original from_ref, just return w_some_obj
        return space.w_object
    monkeypatch.setattr(pyobject, 'from_ref', from_ref)
    checkmodule('cpyext', '_rawffi')
