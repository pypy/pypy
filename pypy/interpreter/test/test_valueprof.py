from pypy.interpreter.valueprof import *

class Value():
    pass


class ValueInt(Value):
    def __init__(self, val):
        self.intval = val


class ValueProf(ValueProf):
    def is_int(self, val):
        return isinstance(val, ValueInt)

    def get_int_val(self, val):
        return val.intval


def test_int():
    v = ValueProf()
    assert v._vprof_status == SEEN_NOTHING
    v.see_write(ValueInt(1))
    v.see_write(ValueInt(1))
    v.see_write(ValueInt(1))
    v.see_write(ValueInt(1))
    assert v.read_constant_int() == 1
    assert v._vprof_status == SEEN_INT
    v.see_int(2)
    assert v._vprof_status == SEEN_TOO_MUCH
    v.see_int(1)
    assert v._vprof_status == SEEN_TOO_MUCH
    v.see_int(2)
    assert v._vprof_status == SEEN_TOO_MUCH
    v.see_int(3)
    assert v._vprof_status == SEEN_TOO_MUCH

    v = ValueProf()
    assert v._vprof_status == SEEN_NOTHING
    v.see_write(ValueInt(1))
    v.see_write(Value())
    assert v._vprof_status == SEEN_TOO_MUCH
    v.see_write(Value())
    assert v._vprof_status == SEEN_TOO_MUCH


def test_obj():
    v = ValueProf()
    value = Value()
    assert v._vprof_status == SEEN_NOTHING
    v.see_write(value)
    v.see_write(value)
    v.see_write(value)
    v.see_write(value)
    assert v.try_read_constant_obj() is value
    assert v._vprof_status == SEEN_OBJ
    v.see_int(2)
    assert v._vprof_status == SEEN_TOO_MUCH

    v = ValueProf()
    assert v._vprof_status == SEEN_NOTHING
    v.see_write(Value())
    v.see_write(Value())
    assert v._vprof_status == SEEN_TOO_MUCH


def test_none():
    v = ValueProf()
    assert v._vprof_status == SEEN_NOTHING
    v.see_write(None)
    assert v._vprof_status == SEEN_TOO_MUCH
    v.see_write(None)
    assert v._vprof_status == SEEN_TOO_MUCH

    v = ValueProf()
    v.see_write(ValueInt(1))
    assert v._vprof_status == SEEN_INT
    v.see_write(None)
    assert v._vprof_status == SEEN_TOO_MUCH

    v = ValueProf()
    v.see_write(Value())
    assert v._vprof_status == SEEN_OBJ
    v.see_write(None)
    assert v._vprof_status == SEEN_TOO_MUCH
