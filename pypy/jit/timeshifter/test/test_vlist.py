from pypy.jit.hintannotator.annotator import HintAnnotatorPolicy
from pypy.jit.timeshifter.test.test_timeshift import TimeshiftingTests

P_OOPSPEC = HintAnnotatorPolicy(novirtualcontainer=True, oopspec=True)


class TestVList(TimeshiftingTests):

    def test_vlist(self):
        def ll_function():
            lst = []
            lst.append(12)
            return lst[0]
        res = self.timeshift(ll_function, [], [], policy=P_OOPSPEC)
        assert res == 12
        self.check_insns({})

    def test_enter_block(self):
        def ll_function(flag):
            lst = []
            lst.append(flag)
            lst.append(131)
            if flag:
                return lst[0]
            else:
                return lst[1]
        res = self.timeshift(ll_function, [6], [], policy=P_OOPSPEC)
        assert res == 6
        self.check_insns({'int_is_true': 1})
        res = self.timeshift(ll_function, [0], [], policy=P_OOPSPEC)
        assert res == 131
        self.check_insns({'int_is_true': 1})

    def test_merge(self):
        def ll_function(flag):
            lst = []
            if flag:
                lst.append(flag)
            else:
                lst.append(131)
            return lst[-1]
        res = self.timeshift(ll_function, [6], [], policy=P_OOPSPEC)
        assert res == 6
        self.check_insns({'int_is_true': 1})
        res = self.timeshift(ll_function, [0], [], policy=P_OOPSPEC)
        assert res == 131
        self.check_insns({'int_is_true': 1})

    def test_replace(self):
        def ll_function(flag):
            lst = []
            if flag:
                lst.append(12)
            else:
                lst.append(131)
            return lst[-1]
        res = self.timeshift(ll_function, [6], [], policy=P_OOPSPEC)
        assert res == 12
        self.check_insns({'int_is_true': 1})
        res = self.timeshift(ll_function, [0], [], policy=P_OOPSPEC)
        assert res == 131
        self.check_insns({'int_is_true': 1})

    def test_force(self):
        def ll_function(n):
            lst = []
            lst.append(n)
            if n:
                lst.append(12)
            return lst[-1]
        res = self.timeshift(ll_function, [6], [], policy=P_OOPSPEC)
        assert res == 12
        res = self.timeshift(ll_function, [0], [], policy=P_OOPSPEC)
        assert res == 0

    def test_oop_vlist(self):
        def ll_function():
            lst = [3, 5]
            five = lst.pop()        # [3]
            lst.append(len(lst))    # [3, 1]
            lst2 = list(lst)
            three = lst.pop(0)      # [1]
            lst.insert(0, 8)        # [8, 1]
            lst.insert(2, 7)        # [8, 1, 7]
            lst.append(not lst)     # [8, 1, 7, 0]
            lst.reverse()           # [0, 7, 1, 8]
            lst3 = lst2 + lst       # [3, 1, 0, 7, 1, 8]
            del lst3[1]             # [3, 0, 7, 1, 8]
            seven = lst3.pop(2)     # [3, 0, 1, 8]
            lst3[0] = 9             # [9, 0, 1, 8]
            nine = lst3.pop(-4)     # [0, 1, 8]
            return (len(lst3) * 10000000 +
                    lst3[0]   *  1000000 +
                    lst3[1]   *   100000 +
                    lst3[-1]  *    10000 +
                    five      *     1000 +
                    three     *      100 +
                    seven     *       10 +
                    nine      *        1)
        assert ll_function() == 30185379
        res = self.timeshift(ll_function, [], [], policy=P_OOPSPEC)
        assert res == 30185379
        self.check_insns({})

    def test_alloc_and_set(self):
        def ll_function():
            lst = [0] * 9
            return len(lst)
        res = self.timeshift(ll_function, [], [], policy=P_OOPSPEC)
        assert res == 9
        self.check_insns({})
        
