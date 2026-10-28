import pytest
from rpython.rlib.rarithmetic import r_longlong
from pypy.interpreter.error import OperationError
from pypy.module.time.timeutils import timestamp_w
from pypy.module.time.interp_time import _format_has_y

def test_timestamp_w(space):
    w_1_year = space.newint(365 * 24 * 3600)
    result = timestamp_w(space, w_1_year)
    assert isinstance(result, r_longlong)
    assert result // 10 ** 9 == space.int_w(w_1_year)
    w_millenium = space.mul(w_1_year, space.newint(1000))
    with pytest.raises(OperationError):  # timestamps overflow after ~300 years
        timestamp_w(space, w_millenium)

def test_format_has_y():
    assert _format_has_y('%y')
    assert _format_has_y('date: %Y-%m-%d, short %y')
    assert _format_has_y('%#y')
    assert _format_has_y('%%%y')             # literal '%', then %y
    assert not _format_has_y('')
    assert not _format_has_y('%Y')
    assert not _format_has_y('no directives here')
    assert not _format_has_y('%%y')          # literal '%' then a plain 'y'
    assert not _format_has_y('%')
    assert not _format_has_y('%#')
