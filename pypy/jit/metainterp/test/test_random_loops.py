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
        print "check('%s'," % bytecode, args, ',%d)' % max_back_jumps
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
        return '{{' + self.block() + '}}'


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

    def test_failure1(self):
        self.check('{{7d<(37>(c6-A{a6>n(x)5b<()(bb+Bea-A){7d>n(x)1e+A7d-B3d+E35+Eac-B2b<(04+Cxe8+D9d+C)(){c6<n(x)ad+B6a+Cx20-Cce+Ac8-D}}{b9>n(x)a5=(2c+E)(xxe9-A)ec>(b7-A40+Ce0-Cx06-A)(xc0-Ad2-A1e+B0d+Bx09+B0b-D)}be-Ab7=(3a+Ab7-Dde<(x))(ec+Cd4+D5d<(x10+A)(cb-Cb9-C))59<(2b-C00-Ab0<(bc-Bde+Bxa2-E4d+A))(e7+Eb3<(c4-Bxx)59-C7c+Aa8>(96-Exce+D3e-Ex)db+A76-Cdb-Bdc=(2b-A))}d2+D)(27-C26+B39+A9d+Bcc+Dab+Cdd=(ae+Eee-Ex{5d>n(x)}d0<(2a+C41+Dca+C6a>(47-Ae9-Eb7+Cx60+D63-C)bb+D9e+Ec5=(d2-Cxaa-D84-Ced+B20+A4c+B)65+A59-E)ed<(cd+B{a8=n(x)ed+Bxxd8+A}ba-D{66=n(x)a4+D30+Acd+C1c+A6c+Ac7-Dxc0+B}x)4b-Dx)e4-D{aa=n(x)44-Eac>(3e+Aae+A12<(a4-A)99<(ce-C4a+A7b+Dxdd+E)(c5+A10-D63-Eda-E22-E85+Dea+E)x)ed+Dbb=(e5-A9e-C)(x{ca<n(x)ad-Caa+E}d5+Eb3-E)b8+Cd8-D8b+Bd1<(e6+E{be<n(x)d2+A88+D70-D23-Ex}cb-Dx)(e0<(a8+E)4e-A8c+C{d9=n(x)}20+Cx8a-Bx)e6-A}))(ac<(ec<({7d<n(x)29-C}e0=(19+C0c+C5e-Bc2=()(78+Da9-B5d-Aa3+Bxea-Dx)1a+C)x)x54-C)(c8<()(5a+A9d+E7a-D56+Cae-Dx{62=n(x){b2<n(x)}{8e>n(x)}e5+Ba5+B}c9=()c0=(7b-Ae1+Daa+Aed+C)(91-C))3d=(a2>(1e-Cba=(2c-A)21+C6b>(aa-Bxd5-Bc7-E)ab<(8c-Ba8-Cxea-D4e+Ae8+Dc5+Ade+B)x33+B5a-C17+D)2a+B{eb<n(x)xx85=(cc+A3d-E)(xe4-D81+C6d-D28-Aee+A47+Cx){1a>n(x)x6a+Cb4+A27-Eab-C35-E25+B1d+C}cc+Aae-D}cc+C61-C68-D)(xe4>(e4+Db4-Cxdb=(xc7-Bcd-Bde-A00+A39+E9c+Dc9+B24-B){2b>n(x)x4d+E8d+Dbb+Ce7-Bxea+B54+A}80-A43<(89-B)(1c+Cx7b+Ae2+E02-C84+Exd0+A))(3d+Eb3-Ecd-A{8c=n(x)37-Bb0+Axxee+C11-C2c-De6-D46+D}cb+E)84+B05-Cbd+D)ad>(b6-C7d+Ae4-B4a+E)34-Cx9a=({c4>n(x)dd+B72<(a9+A)(b0-Db8-Dac-Bba-Excb+Ce2+Bx)ba-Bda+Cce-Cx}78+E97=(aa+Dx67+Dbc+B{de>n(x)b8-C14-Cx})c4+Cac+Ex80+C))xca=({55<n(x)}be+A)9a+E0a+A{34=n(x)9d<(x11-D4a-C48-E)({36=n(x)}e7+Cae=(05-A{c2=n(x)b2-C09-Ded-C}ea>(de+Ax)da-B{d6>n(x)8d+A36-Bx8d-Bx49+Bbc-D88+Bx}x26-Da7-E)({9c>n(x)}bc<(0a-Cx61+Cce+A54-Ce7+A21-C9d+D)(6d-E)x{7e=n(x)6d-Ce6-Cx}5c>(bd+Ed5+Cc0-Dc2+C93-B)x69>(d9-Ac8+B8c-Dx94-E76+Ax)(ba+D)b6>(bb+Ebb-A5e+Bc3-D6c-E))54>(95+B46-D{15<n(x)da+D}0d+Acd<(ce-Bxe9+E41+Ba8+C)(d7-Exa0+A)5c+Da5>(xb6+Ec6-Aac-Bxc2-Ax99-C))b0-E58>(x0e+Bxa4+D5e>(7e-Dde-B1c+Bba-B8a-D)(35-Cce-C4c-C90-C1e+B9a+Be7+C1d-E)45>(xb9+A91+Ecc-Aac-B91+Cd1-De3+Ddd-B)c0+A0a>(45+Cbd+Bdc+Db4-D7c+C29+A7a+B60+A))(5d>(xx6e-Dxea+C)(c2-Cad+D36-Cx)61+E20-C9e-Cc2+Cce+Ad0+B{4b=n(x)})x{a1=n(x)e8<(x35-Dd3-Bd6-Bea+Eac-Acc+B79+Eaa-C)}x)xc7>(6b-C{57>n(x)e2>(1a+A97+Dxcc-E7b+A5d-B82+C2b-B)0a+Be1-Cbc+Ca2-E01+B{41>n(x)e1+Dc6+B47+Beb+Ac2+Bxab+D}}d3-D0e+E0d+Bae=(c7+Ce3-Bc3<(d2+E68+Bbc-Cdc+B1b-Ea2-Ac8-E)45-B43+Aac-E)xbe+C)dc=({ee>n(x)a4-Axd2+B1b+B}aa+Exxxb4>()(cb-C{4d<n(x)e3+Ea0-C}a7+B85-Cc6=(6c-De6-E51+A8e+D2a-Eda+B82+B)(c1-Aae-Bcc+Excc+D6e+B)3e-C)38-A52-Cx)(e4<({b7<n(x)d0+E8c+Dec+Ae3+A9d+C18-D}78+Cc3=(x44+Exx42-Ecd-Bb9+E33-D)c5=(12-Bcd+Ca8-B)(20+Ba6+A74-Dbc-Ex89-Dx4b-Dc7+B)31>(a0-Dab+A8c+Ddd-Edc+A)(xce-D)de=(d6+E83+Cxxc6-Axx)(0b+D78+Cx07-Eda+Ax1d-Eba+A)e6+E)de-E1c+Aae=(20-B25+Dba>(xxx71-A2b+Dc7+E){e9=n(x)7b+Ecd+Bda-Eec-A4b+De7-Ae3-D}ae+C7c+Aaa+Bx)86+B)}{cc=n(x)6b-B{cd<n(x)12=(3a+Cb9-C{5d<n(x)}e1>(cc+D7e-Bc0+Bxde-A2c-B5d-C)(ba+D2b-Axxx07+Ca4-C)eb-C23-D7e<(xb8+Edd-De1+Add+C35-Dxx)x)(87-Ccc+Ee2=(9a-E78-C)()cb-A)39+D0b-Aa4>(ca+A)c6=({9c<n(x)ab-D0c+Bb1+Dxx49-Bx}73+Dx5a-D)(44>(bb-E22-D)x5e-C11<()9b=(6d-Bcd+A9e-E2a-E38+B4e-C)xaa-B{82=n(x)ae-B6a-Ab7+Ca9-A}08+C)d7+Cxcb-A}6c-B9c+D9c-E})3d+Cd4>(xab<()()3e+Ebd-Ba0-B{6c<n(x)e6+Dac+B{d9=n(x)}6d-E92-Axx67-Bd5=(00>(63+Eb5+Bxec<(a1+E4e+Axdc-C)ea+Eaa=(x37-Edd-Cb4+B)(43-Ae0-Bx7e-C94+A)e8-Bd1-Da8-D)())(ce=(6c-B10+C7a+A3d+Ax19+Aca+B)(ed+A)1d>()d1+Ex43+A9d+Eb5+A)}8d+Ae9-C)(3d-D6c+Ee9<(29-C4c=({e9<n(x)}))31-Dxb3-C)a3=(e6-C{c9=n(x)3a>(4c+B)8a-Dc0-E82+E50+D}a1+D98=(be-B)3a-Ae9+De2-Add-E)35-D}}', [13, 40, 35, 44, 76], 1000)

    def test_failure2(self):
        self.check('{{d2-Bab-D48<(e3-E0d+Eac-B1d>(9b>(25>(14+Da9-Eb9-B{05=n(x)bb+Cb2+Ee6+C}35-Acd+E)(c4-Exaa-A{ce=n(x)}0c+E)7e<(0b-B85-Dc9-Bb2-Dcc<(x11+A9a+Cx)(xxde+Da8+B)6b-Ada-D)aa+D))73+D{dc=n(x)d9-Bea+A8e=(81<(e8-D)(94+B8c+D9d-E{ee=n(x)a0+Dx43-Bx}a0+B56+Ca7-C4e=(01-C4c+Dxa7-B))3a-Cae-B50+Cb3-Aee+D4b-Bb5+B)}ed+Ea6>(ab+Abb-C86+B{b9<n(x){db>n(x){b1>n(x)21+C}3e=(db+Excd-Dx21+C)48-B}{6a<n(x)ce+D1d+C{2d<n(x)c0-A96+Be3-E5d-B2d-E}55-D9c<(x3b-Ceb-A98+Abc-A)()ee+Cca+E{de<n(x)3c+Dxx7d-Bcd-Cd1-D}{ea<n(x)29+Cb8-C6a+Dda-A3b-A96+B9e+Cdb-Cx}}xe7>(x{0b<n(x)28+Ex0c-Dcb-Bxbd-B96+D})4a-C56+C6c+B}x))6a-E6e+E}}', [49, 58, 34, 95, 30], 59)

    def test_random_bytecode(self):
        for i in xrange(1000):
            yield self.check, self.random_loop(), [randrange(100) for i in xrange(5)], 1000

class TestLLtype(BaseTests, LLJitMixin):
    pass
