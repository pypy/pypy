from collections.abc import Sequence, Mapping

def test_patma_flags():
    class A:
        pass

    assert not A.__flags__ & (1 << 5)
    Sequence.register(A)
    assert A.__flags__ & (1 << 5)

def test_subclassing():
    class A:
        pass
    Sequence.register(A)

    assert A.__flags__ & (1 << 5)
    class B(A):
        pass
    assert B.__flags__ & (1 << 5)

def test_multiple():
    class A(Sequence, Mapping):
        pass
    assert A.__flags__ & (1 << 5)
    class B(Mapping, Sequence):
        pass
    assert B.__flags__ & (1 << 6)
