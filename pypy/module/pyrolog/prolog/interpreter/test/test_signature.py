from prolog.interpreter.signature import Signature, SignatureFactory


def test_eq():
    sig1 = Signature("a", 0)
    assert sig1.eq(sig1)
    sig2 = Signature("a", 0)
    assert sig1.eq(sig2)

    sig3 = Signature("a", 1)
    assert not sig1.eq(sig3)

    sig4 = Signature("b", 0)
    assert not sig1.eq(sig4)

def test_cache():
    factory = SignatureFactory()
    sig1 = factory.getsignature("a", 0)
    sig2 = factory.getsignature("a", 0)
    assert sig1 is sig2
    assert sig1.cached

    assert sig1.ensure_cached() is sig1

    sig2 = factory.getsignature("abc", 0, cache=False)
    sig1 = factory.getsignature("abc", 0)
    assert not sig2.cached
    assert sig2.ensure_cached() is sig1

    sig3 = factory.getsignature("xyz", 0, cache=False)
    assert not sig3.cached
    assert sig3.ensure_cached() is sig3
    assert sig3.cached

def test_extra_attr():
    factory = SignatureFactory()
    factory.register_extr_attr("foo", default=5)
    sig1 = factory.getsignature("a", 0)
    assert sig1.get_extra("foo") == 5
    sig1.set_extra("foo", 6)
    assert sig1.get_extra("foo") == 6

    sig1 = factory.getsignature("b", 0, cache=False)
    sig2 = factory.getsignature("b", 0)
    assert sig2.get_extra("foo") == 5
    sig2.set_extra("foo", 6)
    assert sig1.get_extra("foo") == 6


def test_extra_attr_engine():
    factory = SignatureFactory()
    factory.register_extr_attr("foo", engine=True)
    sig1 = factory.getsignature("a", 0)
    e1 = "e1"
    e2 = "e2"
    sig1.set_extra_engine_local("foo", 6, e1)
    assert sig1.get_extra_engine_local("foo", e1) == 6
    assert sig1.get_extra_engine_local("foo", e2) is None
    assert sig1.get_extra_engine_local("foo", e1) is None
    sig1.set_extra_engine_local("foo", 8, e2)
    assert sig1.get_extra_engine_local("foo", e2) == 8

def test_atom_signature():
    factory = SignatureFactory()
    factory.register_extr_attr("foo", engine=True)
    sig1 = factory.getsignature("a", 0)
    assert sig1.atom_signature is sig1
    sig2 = factory.getsignature("a", 5)
    assert sig2.atom_signature is sig1
