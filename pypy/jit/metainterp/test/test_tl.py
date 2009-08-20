import py
from pypy.rlib.jit import JitDriver
from pypy.jit.metainterp.policy import StopAtXPolicy
from pypy.jit.metainterp.test.test_basic import OOJitMixin, LLJitMixin


class ToyLanguageTests:

    def test_tiny1(self):
        myjitdriver = JitDriver(greens = ['s', 'pc'],
                                reds = ['y', 'acc'])

        def ll_plus_minus(s, x, y):
            acc = x
            pc = 0
            while pc < len(s):
                myjitdriver.can_enter_jit(y=y, pc=pc, acc=acc, s=s)
                myjitdriver.jit_merge_point(y=y, pc=pc, acc=acc, s=s)
                op = s[pc]
                if op == '+':
                    acc += y
                elif op == '-':
                    acc -= y
                pc += 1
            return acc

        codes = ["++++++++++", "+-++---+-++-"]
        def main(n, x, y):
            code = codes[n]
            return ll_plus_minus(code, x, y)

        res = self.meta_interp(main, [0, 100, 2])
        assert res == 120

    def test_tlr(self):
        from pypy.jit.tl.tlr import interpret, SQUARE

        codes = ["", SQUARE]
        def main(n, a):
            code = codes[n]
            return interpret(code, a)

        res = self.meta_interp(main, [1, 10])
        assert res == 100

    def setup_class(cls):
        from pypy.jit.tl.tl import interp_without_call
        from pypy.jit.tl.tlopcode import compile

        code = compile('''
                PUSH 1   #  accumulator
                PUSH 7   #  N

            start:
                PICK 0
                PUSH 1
                LE
                BR_COND exit

                SWAP
                PICK 1
                MUL
                SWAP
                PUSH 1
                SUB
                PUSH 1
                BR_COND start

            exit:
                POP
                RETURN
        ''')

        code2 = compile('''
                PUSHARG
            start:
                PUSH 1
                SUB
                PICK 0
                PUSH 1
                LE
                BR_COND exit
                PUSH 1
                BR_COND start
            exit:
                RETURN
        ''')
        
        codes = [code, code2]
        def main(n, inputarg):
            code = codes[n]
            return interp_without_call(code, inputarg=inputarg)
        cls.main = main

    def test_tl_base(self):
        # 'backendopt=True' is used on lltype to kill unneeded access
        # to the class, which generates spurious 'guard_class'
        res = self.meta_interp(self.main.im_func, [0, 6], listops=True,
                               backendopt=True)
        assert res == 5040
        self.check_loops({'int_mul':1, 'jump':1,
                          'int_sub':1, 'int_is_true':1, 'int_le':1,
                          'guard_false':1, 'guard_value':1})

    def test_tl_2(self):
        res = self.meta_interp(self.main.im_func, [1, 10], listops=True,
                               backendopt=True)
        assert res == self.main.im_func(1, 10)
        self.check_loops({'int_sub':1, 'int_le':1,
                         'int_is_true':1, 'guard_false':1, 'jump':1,
                          'guard_value':1})

    def test_tl_call(self, listops=True, policy=None):
        from pypy.jit.tl.tl import interp
        from pypy.jit.tl.tlopcode import compile
        from pypy.jit.metainterp import simple_optimize

        code = compile('''
              PUSHARG
          start:
              PUSH 1
              SUB
              PICK 0
              PUSH 0
              CALL func
              POP
              GT
              BR_COND start
          exit:
              RETURN
          func:
              PUSH 0
          inside:
              PUSH 1
              ADD
              PICK 0
              PUSH 3
              LE
              BR_COND inside
              PUSH 1
              RETURN
              ''')
        assert interp(code, inputarg=100) == 0
        codes = [code, '']
        def main(num, arg):
            return interp(codes[num], inputarg=arg)
        
        res = self.meta_interp(main, [0, 20], optimizer=simple_optimize,
                               listops=listops, backendopt=True, policy=policy)
        assert res == 0

    def test_tl_call_full_of_residuals(self):
        # This forces most methods of Stack to be ignored and treated as
        # residual calls.  It tests that the right thing occurs in this
        # case too.
        from pypy.jit.tl.tl import Stack
        methods = [Stack.put,
                   Stack.pick,
                   Stack.roll,
                   Stack.append,
                   Stack.pop]
        methods = [m.im_func for m in methods]
        self.test_tl_call(listops=False, policy=StopAtXPolicy(*methods))


class TestOOtype(ToyLanguageTests, OOJitMixin):
    def test_tl_call_full_of_residuals(self):
        py.test.skip("virtualizables: in-progress with ootype")

class TestLLtype(ToyLanguageTests, LLJitMixin):
    pass
