import pytest
from rpython.rlib import rvmprof

class FakeVMProf(object):

    def __init__(self):
        self._enabled = False
        self._ignore_signals = 1

    # --- VMProf official API ---
    # add fake methods as needed by the tests

    def stop_sampling(self):
        self._ignore_signals += 1

    def start_sampling(self):
        assert self._ignore_signals > 0, ('calling start_sampling() without '
                                          'the corresponding stop_sampling()?')
        self._ignore_signals -= 1

    # --- FakeVMProf specific API ---
    # this API is not part of rvmprof, but available only inside tests using
    # fakervmprof

    @property
    def is_sampling_enabled(self):
        return self._ignore_signals == 0


@pytest.fixture
def fakevmprof(request, monkeypatch):
    fake = FakeVMProf()
    def _get_fake_vmprof():
        return fake
    monkeypatch.setattr(rvmprof.rvmprof, '_get_vmprof', _get_fake_vmprof)
    return fake

