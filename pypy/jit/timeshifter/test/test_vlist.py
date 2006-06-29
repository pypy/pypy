from pypy.annotation.policy import AnnotatorPolicy
from pypy.jit.timeshifter.test.test_timeshift import timeshift

P_OOPSPEC = AnnotatorPolicy()
P_OOPSPEC.novirtualcontainer = True
P_OOPSPEC.oopspec = True


def test_vlist():
    def ll_function():
        lst = []
        lst.append(12)
        return lst[0]
    insns, res = timeshift(ll_function, [], [], policy=P_OOPSPEC)
    assert res == 12
    assert insns == {}
