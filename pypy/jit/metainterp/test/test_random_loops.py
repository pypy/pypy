from pypy.jit.metainterp.test.support import LLJitMixin
from pypy.rlib.jit import JitDriver
from random import choice, randrange
from pypy.rlib.rarithmetic import intmask
import re

class IntBox(object):
    def __init__(self, val):
        self.val = val

    def value(self):
        return self.val

    def add(self, other):
        return IntBox(intmask(self.value() + other.value()))

    def sub(self, other):
        return IntBox(intmask(self.value() - other.value()))

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
                elif op == 'n':
                    value = IntBox(not value.value())
                elif op == '{':
                    loop_stack.append(pc)
                elif op == '}':
                    pc -= offsets[pc] - 1
                    prev = current
                    if max_back_jumps > 0:
                        max_back_jumps -= 1
                        if not max_back_jumps:
                            break
                    myjitdriver.can_enter_jit(pc=pc, a=a, b=b, c=c, d=d, e=e, value=value, prev=prev,
                                              loop_stack=loop_stack, max_back_jumps=max_back_jumps)
                    continue
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

    def while_loop(self):
        self.levels -= 1
        code = '{' + self.compare() + 'n(x)' + self.block() + '}'
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
            stmts += [self.while_loop, self.if_block, self.if_else_block]
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
        self.check('0A9B{ab+Ab1-Bbn(x)}', a=45)

    def test_conditional(self):
        self.check('0A0C9B{b4<(a1+A)(c1+C)b1-Bbn(x)}', c=6, a=3)

    def test_break(self):
        self.check('0A9B{ab+Ab1-Bb0=(x)}', a=45)

    def test_nested(self):
        self.check('''0A
                      9B{
                        9C{
                          ab+A
                          ac+A
                          c1-C
                          c0= (x)
                        }
                        b1-B
                        b0= (x)
                      }''', a=810)

    def test_jump_limit(self):
        self.check('0A{a1+A}', max_back_jumps=10, a=10)

    def test_overflow(self):
        self.check('9A{aa+A}', max_back_jumps=100)
        self.check('09-A{aa+A}', max_back_jumps=100)

    def test_random_bytecode(self):
        for i in xrange(1000):
            yield self.check, self.random_loop(), [randrange(100) for i in xrange(5)], 1000

class TestLLtype(BaseTests, LLJitMixin):
    pass
