from pypy.annotation.policy import AnnotatorPolicy
from pypy.jit.timeshifter.test.test_timeshift import TimeshiftingTests

P_OOPSPEC = AnnotatorPolicy()
P_OOPSPEC.novirtualcontainer = True
P_OOPSPEC.oopspec = True


class TestVDict(TimeshiftingTests):

    def test_vdict(self):
        def ll_function():
            dic = {}
            dic[12] = 34
            dic[13] = 35
            return dic[12]
        res = self.timeshift(ll_function, [], [], policy=P_OOPSPEC)
        assert res == 34
        self.check_insns({})

    def test_vdict_and_vlist(self):
        def ll_function():
            dic = {}
            lst = [12]
            dic[12] = 34
            dic[13] = 35
            return dic[lst.pop()]
        res = self.timeshift(ll_function, [], [], policy=P_OOPSPEC)
        assert res == 34
        self.check_insns({})
