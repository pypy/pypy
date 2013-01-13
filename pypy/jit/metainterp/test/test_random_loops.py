from pypy.jit.metainterp.test.support import LLJitMixin
from pypy.rlib.jit import JitDriver

class IntBox(object):
    def __init__(self, val):
        self.val = val

    def value(self):
        return self.val

    def add(self, other):
        return IntBox(self.value() + other.value())

    def sub(self, other):
        return IntBox(self.value() - other.value())

class RandomLoopBase(object):
    def check(self, bytecode, args=(0,0,0,0,0), **kwargs):
        myjitdriver = JitDriver(greens = ['pc'], reds = ['a', 'b', 'c', 'd', 'e', 'value', 'prev'])
        def interpreter(_a, _b, _c, _d, _e):
            pc = 0
            value = prev = IntBox(0)
            a = IntBox(_a)
            b = IntBox(_b)
            c = IntBox(_c)
            d = IntBox(_d)
            e = IntBox(_e)
            while pc < len(bytecode):
                myjitdriver.jit_merge_point(pc=pc, a=a, b=b, c=c, d=d, e=e, value=value, prev=prev)
                op = bytecode[pc]
                current = value

                if '0' <= op <= '9':
                    value = IntBox(ord(op) - ord('0'))
                elif op == 'a':
                    value = a
                elif op == 'b':
                    value = b
                elif op == 'c':
                    value = c
                elif op == 'd':
                    value = d
                elif op == 'e':
                    value = e
                elif op == 'A':
                    a = value
                elif op == 'B':
                    b = value
                elif op == 'C':
                    c = value
                elif op == 'D':
                    d = value
                elif op == 'E':
                    e = value
                elif op == '+':
                    value = prev.add(value)
                elif op == '-':
                    value = prev.sub(value)
                else:
                    assert False

                prev = current
                pc += 1
            return a.value(), b.value(), c.value(), d.value(), e.value()
        
        obj = self.meta_interp(interpreter, args)._obj
        res = {'a': obj.item0, 'b': obj.item1, 'c': obj.item2, 'd': obj.item3, 'e': obj.item4}
        obj = interpreter(*args)
        expected = {'a': obj[0], 'b': obj[1], 'c': obj[2], 'd': obj[3], 'e': obj[4]}
        assert res == expected

        for var, val in kwargs.items():
            assert res[var] == val
        return res



class BaseTests(RandomLoopBase):
    def test_basic(self):
        self.check('1A2B3C4D5E', a=1, b=2, c=3, d=4, e=5)
        self.check('1', [6,7,8,9,0], a=6, b=7, c=8, d=9, e=0)
        self.check('1a+A2b+B3c+C4d+D5e+E', [6,7,8,9,0], a=7, b=9, c=11, d=13, e=5)
        self.check('ea+Eeb+Eec+Eed+E', [6,7,8,9,0], a=6, b=7, c=8, d=9, e=30)

class TestLLtype(BaseTests, LLJitMixin):
    pass
