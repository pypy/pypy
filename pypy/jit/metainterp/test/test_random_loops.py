from pypy.jit.metainterp.test.support import LLJitMixin
from pypy.rlib.jit import JitDriver
from random import choice, randrange
import re

class IntBox(object):
    def __init__(self, val):
        self.val = val

    def value(self):
        return self.val

    def add(self, other):
        return IntBox(self.value() + other.value())

    def sub(self, other):
        return IntBox(self.value() - other.value())

    def gt(self, other):
        return IntBox(self.value() > other.value())

    def lt(self, other):
        return IntBox(self.value() < other.value())

    def eq(self, other):
        return IntBox(self.value() == other.value())


class UnknonwOpCode(Exception):
    pass

class RandomLoopBase(object):
    def check(self, bytecode, args=(0,0,0,0,0), max_back_jumps=-1, **kwargs):
        print 'check:', bytecode, args, max_back_jumps
        bytecode = re.subn('\s', '', bytecode)[0]
        offsets = self.offsets(bytecode)
        assert len(args) == 5
        for n in kwargs.keys():
            assert n in 'abcde'
        args = tuple(args) + (max_back_jumps,)
        def get_printable_location(pc):
            return bytecode[pc]
        myjitdriver = JitDriver(greens = ['pc'], reds = ['max_back_jumps', 'a', 'b', 'c', 'd', 'e', 
                                                         'value', 'prev', 'loop_stack'],
                                get_printable_location=get_printable_location)
        def interpreter(_a, _b, _c, _d, _e, max_back_jumps):
            pc = 0
            value = prev = IntBox(0)
            a = IntBox(_a)
            b = IntBox(_b)
            c = IntBox(_c)
            d = IntBox(_d)
            e = IntBox(_e)
            loop_stack = []
            while pc < len(bytecode):
                myjitdriver.jit_merge_point(pc=pc, a=a, b=b, c=c, d=d, e=e, value=value, prev=prev, 
                                            loop_stack=loop_stack, max_back_jumps=max_back_jumps)
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
                elif op == '>':
                    value = prev.gt(value)
                elif op == '<':
                    value = prev.lt(value)
                elif op == '=':
                    value = prev.eq(value)
                elif op == '{':
                    loop_stack.append(pc)
                elif op == '}':
                    if value.value():
                        pc -= offsets[pc] - 1
                        prev = current
                        if max_back_jumps > 0:
                            max_back_jumps -= 1
                            if not max_back_jumps:
                                break
                        myjitdriver.can_enter_jit(pc=pc, a=a, b=b, c=c, d=d, e=e, value=value, prev=prev,
                                                  loop_stack=loop_stack, max_back_jumps=max_back_jumps)
                        continue
                    else:
                        loop_stack.pop()
                elif op == 'x':
                    pc = loop_stack.pop()
                    pc += offsets[pc]
                elif op == '(':
                    if not value.value():
                        value = IntBox(1)
                        pc += offsets[pc]
                elif op == ')':
                    value = IntBox(0)
                else:
                    raise UnknonwOpCode

                prev = current
                pc += 1
            return a.value(), b.value(), c.value(), d.value(), e.value()
        
        obj = interpreter(*args)
        expected = {'a': obj[0], 'b': obj[1], 'c': obj[2], 'd': obj[3], 'e': obj[4]}
        for var, val in kwargs.items():
            assert expected[var] == val

        obj = self.meta_interp(interpreter, args)._obj
        res = {'a': obj.item0, 'b': obj.item1, 'c': obj.item2, 'd': obj.item3, 'e': obj.item4}
        assert res == expected

        return res

    def offsets(self, bytecode):
        offsets = [0] * len(bytecode)
        stack = []
        for pc, op in enumerate(bytecode):
            if op in '{[(':
                stack.append((pc, op))
            elif op in ')]}':
                start_pc, start_op = stack.pop()
                assert start_op + op in ('()', '[]', '{}')
                offsets[start_pc] = offsets[pc] = pc - start_pc
        return offsets

    def variable(self):
        return choice('abcde')

    def constant(self):
        return choice('0123456789')

    def value(self):
        return choice([self.variable, self.constant])()

    def binop(self):
        return self.value() + self.value() + choice('+-') + self.variable().upper()

    def break_loop(self):
        return 'x'

    def compare(self):
        return self.value() + self.value() + choice('<>=')

    def do_while(self):
        self.levels -= 1
        code = '{' + self.block() + self.compare() + '}'
        self.levels += 1
        return code

    def if_block(self):
        self.levels -= 1
        code = self.compare() + '(' + self.block() + ')'
        self.levels += 1
        return code

    def if_else_block(self):
        self.levels -= 1
        code = self.compare() + '(' + self.block() + ')(' + self.block() + ')'
        self.levels += 1
        return code

    def block(self):
        stmts = [self.break_loop] + [self.binop] * 5
        if self.levels:
            stmts += [self.do_while, self.if_block, self.if_else_block]
        return ''.join(choice(stmts)() for i in xrange(randrange(self.max_stmts_per_block)))

    def random_loop(self, max_stmts_per_block=10, max_levels=5):
        self.max_stmts_per_block = max_stmts_per_block
        self.levels = max_levels
        return '{{' + self.block() + '1}1}'


class BaseTests(RandomLoopBase):
    def test_basic(self):
        self.check('1A2B3C4D5E', a=1, b=2, c=3, d=4, e=5)
        self.check('1', [6,7,8,9,0], a=6, b=7, c=8, d=9, e=0)
        self.check('1a+A2b+B3c+C4d+D5e+E', [6,7,8,9,0], a=7, b=9, c=11, d=13, e=5)
        self.check('ea+Eeb+Eec+Eed+E', [6,7,8,9,0], a=6, b=7, c=8, d=9, e=30)

    def test_loop(self):
        self.check('0A9B{ab+Ab1-Bb}', a=45)

    def test_conditional(self):
        self.check('0A0C9B{b4<(a1+A)(c1+C)b1-Bb}', c=6, a=3)

    def test_break(self):
        self.check('0A9B{ab+Ab1-Bb0=(x)1}', a=45)

    def test_nested(self):
        self.check('''0A
                      9B{
                        9C{
                          ab+A
                          ac+A
                          c1-C
                          c0= (x)
                        1}
                        b1-B
                        b0= (x)
                      1}''', a=810)

    def test_jump_limit(self):
        self.check('0A{a1+A1}', max_back_jumps=10, a=10)

    def test_random_bytecode(self):
        for i in xrange(1000):
            yield self.check, self.random_loop(), [randrange(100) for i in xrange(5)], 1000

    def test_failure1(self):
        self.check('{{c3+A{cc+Dda<({2b=}c7=(cd-Aae-Exe8+Ax)aa+Ab5-D2a-Dba=(0d+Be7-D6e+Bd3-A)0e+D)(a0=(x{79>})(0e>(x)9c+Ce3-Ccb>(5d=(08-Axx)da+B4d<(04-B7d+Eba+Axx09+B15-E))()33-Bc9<()({xba+Ec1+C0a=}4c+C79+Dxda<(0c+A)(5e+D9b+C2d-Bcc+D8b-A99-B3c-De4-Cc9+C)58-Bcc-Ae1-Be9-D)ae+A)xcc=(3c=(d5>(23+Bad+Bx8c-De5-Dac-Cd3-Cea+Ax)(xx)33-A{dc-D0b-Ab8-Cb1+Bd1+A28=}65+Aba<(x5c+Axba-C57+A3b-Deb+C)(cd+Bec+B30+Bbb+D45-De4-C)b8-Eae<(aa+Ce4-E1a+Dxa1+E)(d5-Ea2-Ex62+Bxx6a-D)be+B)c6+C3e+A)(5e+C4e-Ec9+Bx26-Ca8=()x)a3<(x10-Cd8-Aba-Ex{5c=})55+C)xd2-Ax98>}1}1}', [49, 30, 28, 93, 22], 1000)

class TestLLtype(BaseTests, LLJitMixin):
    pass
