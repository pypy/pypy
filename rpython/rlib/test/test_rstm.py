import thread, time
from rpython.rlib import rstm

def test_symbolics():
    assert rstm.adr_nursery_free == rstm.adr_nursery_free
    assert rstm.adr_nursery_free != rstm.adr_nursery_top
