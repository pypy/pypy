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

def test_enter_block():
    def ll_function(flag):
        lst = []
        lst.append(flag)
        lst.append(131)
        if flag:
            return lst[0]
        else:
            return lst[1]
    insns, res = timeshift(ll_function, [6], [], policy=P_OOPSPEC)
    assert res == 6
    assert insns == {'int_is_true': 1}
    insns, res = timeshift(ll_function, [0], [], policy=P_OOPSPEC)
    assert res == 131
    assert insns == {'int_is_true': 1}

def test_merge():
    def ll_function(flag):
        lst = []
        if flag:
            lst.append(flag)
        else:
            lst.append(131)
        return lst[-1]
    insns, res = timeshift(ll_function, [6], [], policy=P_OOPSPEC)
    assert res == 6
    assert insns == {'int_is_true': 1}
    insns, res = timeshift(ll_function, [0], [], policy=P_OOPSPEC)
    assert res == 131
    assert insns == {'int_is_true': 1}

def test_replace():
    def ll_function(flag):
        lst = []
        if flag:
            lst.append(12)
        else:
            lst.append(131)
        return lst[-1]
    insns, res = timeshift(ll_function, [6], [], policy=P_OOPSPEC)
    assert res == 12
    assert insns == {'int_is_true': 1}
    insns, res = timeshift(ll_function, [0], [], policy=P_OOPSPEC)
    assert res == 131
    assert insns == {'int_is_true': 1}
