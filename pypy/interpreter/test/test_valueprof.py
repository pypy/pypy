from pypy.interpreter.valueprof import ValueProf

class Value():
    pass

def test_simple():
    v = ValueProf(2)
    v.see_int(0, 1)
    v.see_int(0, 1)
    v.see_int(0, 1)
    v.see_int(0, 1)
    assert v.values_int[0] == 1
    assert v.counters[0] == -4

    v.see_int(0, 5)
    v.see_int(0, 5)
    v.see_int(0, 5)
    v.see_int(0, 5)
    v.see_int(0, 5)
    assert v.values_int[0] == 5
    assert v.counters[0] == -5

    val1 = Value()
    v.see_object(0, val1)
    v.see_object(0, val1)
    v.see_object(0, val1)
    v.see_object(0, val1)
    assert v.values_wref[0]() is val1
    assert v.counters[0] == 4

    v.see_object(0, None)
    assert v.counters[0] == 0

def test_freeze():
    v = ValueProf(2)
    v.see_int(0, 1)
    v.see_int(0, 1)
    v.see_int(0, 1)
    v.see_int(0, 1)
    v.see_int(0, 1)
    v.see_int(0, 1)
    v.see_int(0, 1)
    v.freeze()
    v.see_int(0, 2)
    assert v.values_int[0] == 1
