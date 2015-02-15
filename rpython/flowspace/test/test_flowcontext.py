""" Unit tests for flowcontext.py """
import pytest
from rpython.flowspace.model import Variable, FSException
from rpython.flowspace.flowcontext import (
    Raise, RaiseImplicit)

@pytest.mark.parametrize('signal', [
    Raise(FSException(Variable(), Variable())),
    RaiseImplicit(FSException(Variable(), Variable())),
])
def test_signals(signal):
    assert signal.rebuild(*signal.args) == signal
