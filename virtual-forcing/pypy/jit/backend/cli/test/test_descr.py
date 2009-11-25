from pypy.rpython.ootypesystem import ootype
from pypy.jit.backend.cli.runner import CliCPU


def test_fielddescr_ootype():
    A = ootype.Instance("A", ootype.ROOT, {"foo": ootype.Signed})
    B = ootype.Instance("B", A)
    descr1 = CliCPU.fielddescrof(A, "foo")
    descr2 = CliCPU.fielddescrof(B, "foo")
    assert descr1 is descr2

def test_call_descr_extra_info():
    FUNC = ootype.StaticMethod([], ootype.Signed)
    ARGS = ()
    descr1 = CliCPU.calldescrof(FUNC, ARGS, ootype.Signed, "hello")
    extrainfo = descr1.get_extra_info()
    assert extrainfo == "hello"

    descr2 = CliCPU.calldescrof(FUNC, ARGS, ootype.Signed, "hello")
    assert descr2 is descr1

    descr3 = CliCPU.calldescrof(FUNC, ARGS, ootype.Signed)
    assert descr3 is not descr1
    assert descr3.get_extra_info() is None
