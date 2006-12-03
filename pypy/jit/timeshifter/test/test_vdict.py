from pypy.jit.hintannotator.annotator import HintAnnotatorPolicy
from pypy.jit.timeshifter.test.test_timeshift import TimeshiftingTests

P_OOPSPEC = HintAnnotatorPolicy(novirtualcontainer = True,
                                oopspec = True)


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

    def test_multiple_vdicts(self):
        def ll_function():
            d1 = {}
            d1[12] = 34
            l1 = [12]
            l2 = ['foo']
            d2 = {}
            d2['foo'] = 'hello'
            return d1[l1.pop()] + len(d2[l2.pop()])
        res = self.timeshift(ll_function, [], [], policy=P_OOPSPEC)
        assert res == 39
        self.check_insns({})
