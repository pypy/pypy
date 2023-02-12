from collections.abc import Sequence, Mapping

def test_patma_flags():
    class A:
        pass

    assert not A.__flags__ & (1 << 5)
    Sequence.register(A)
    assert A.__flags__ & (1 << 5)

