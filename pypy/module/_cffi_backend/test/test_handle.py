import random
from pypy.module._cffi_backend.handle import CffiHandles


class PseudoWeakRef(object):
    _content = 42

    def __call__(self):
        return self._content


def test_cffi_handles_1():
    ch = CffiHandles(None)
    expected_content = {}
    for i in range(10000):
        index = ch.reserve_next_handle_index()
        assert 0 <= index < len(ch.handles)
        assert ch.handles[index]() is None
        pwr = PseudoWeakRef()
        expected_content[index] = pwr
        ch.handles[index] = pwr
    assert len(ch.handles) < 13500
    for index, pwr in expected_content.items():
        assert ch.handles[index] is pwr

def test_cffi_handles_2():
    ch = CffiHandles(None)
    expected_content = {}
    for i in range(10000):
        index = ch.reserve_next_handle_index()
        assert 0 <= index < len(ch.handles)
        assert ch.handles[index]() is None
        pwr = PseudoWeakRef()
        expected_content[index] = pwr
        ch.handles[index] = pwr
        #
        if len(expected_content) > 20:
            r = random.choice(list(expected_content))
            pwr = expected_content.pop(r)
            pwr._content = None
        #
    assert len(ch.handles) < 100
    for index, pwr in expected_content.items():
        assert ch.handles[index] is pwr
