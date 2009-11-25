from pypy.jit.metainterp.history import AbstractFailDescr
from pypy.jit.backend.model import AbstractCPU


def test_faildescr_numbering():
    cpu = AbstractCPU()
    fail_descr1 = AbstractFailDescr()
    fail_descr2 = AbstractFailDescr()    

    n1 = cpu.get_fail_descr_number(fail_descr1)
    n2 = cpu.get_fail_descr_number(fail_descr2)
    assert n1 != n2

    fail_descr = cpu.get_fail_descr_from_number(n1)
    assert fail_descr is fail_descr1
    fail_descr = cpu.get_fail_descr_from_number(n2)
    assert fail_descr is fail_descr2

    # provides interning on its own
    n1_1 = cpu.get_fail_descr_number(fail_descr1)
    assert n1_1 == n1
