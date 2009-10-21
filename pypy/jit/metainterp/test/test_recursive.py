import py
from pypy.rlib.jit import JitDriver, we_are_jitted, OPTIMIZER_SIMPLE
from pypy.jit.metainterp.test.test_basic import LLJitMixin, OOJitMixin
from pypy.jit.metainterp.policy import StopAtXPolicy
from pypy.rpython.annlowlevel import hlstr
from pypy.jit.metainterp.warmspot import CannotInlineCanEnterJit, get_stats

class RecursiveTests:

    def test_simple_recursion(self):
        myjitdriver = JitDriver(greens=[], reds=['n', 'm'])
        def f(n):
            m = n - 2
            while True:
                myjitdriver.jit_merge_point(n=n, m=m)
                n -= 1
                if m == n:
                    return main(n) * 2
                myjitdriver.can_enter_jit(n=n, m=m)
        def main(n):
            if n > 0:
                return f(n+1)
            else:
                return 1
        res = self.meta_interp(main, [20], optimizer=OPTIMIZER_SIMPLE)
        assert res == main(20)

    def test_simple_recursion_with_exc(self):
        myjitdriver = JitDriver(greens=[], reds=['n', 'm'])
        class Error(Exception):
            pass
        
        def f(n):
            m = n - 2
            while True:
                myjitdriver.jit_merge_point(n=n, m=m)
                n -= 1
                if n == 10:
                    raise Error
                if m == n:
                    try:
                        return main(n) * 2
                    except Error:
                        return 2
                myjitdriver.can_enter_jit(n=n, m=m)
        def main(n):
            if n > 0:
                return f(n+1)
            else:
                return 1
        res = self.meta_interp(main, [20], optimizer=OPTIMIZER_SIMPLE)
        assert res == main(20)

    def test_recursion_three_times(self):
        myjitdriver = JitDriver(greens=[], reds=['n', 'm', 'total'])
        def f(n):
            m = n - 3
            total = 0
            while True:
                myjitdriver.jit_merge_point(n=n, m=m, total=total)
                n -= 1
                total += main(n)
                if m == n:
                    return total + 5
                myjitdriver.can_enter_jit(n=n, m=m, total=total)
        def main(n):
            if n > 0:
                return f(n)
            else:
                return 1
        print
        for i in range(1, 11):
            print '%3d %9d' % (i, f(i))
        res = self.meta_interp(main, [10], optimizer=OPTIMIZER_SIMPLE)
        assert res == main(10)
        self.check_enter_count_at_most(10)

    def test_bug_1(self):
        myjitdriver = JitDriver(greens=[], reds=['n', 'i', 'stack'])
        def opaque(n, i):
            if n == 1 and i == 19:
                for j in range(20):
                    res = f(0)      # recurse repeatedly, 20 times
                    assert res == 0
        def f(n):
            stack = [n]
            i = 0
            while i < 20:
                myjitdriver.can_enter_jit(n=n, i=i, stack=stack)
                myjitdriver.jit_merge_point(n=n, i=i, stack=stack)
                opaque(n, i)
                i += 1
            return stack.pop()
        res = self.meta_interp(f, [1], optimizer=OPTIMIZER_SIMPLE, repeat=2,
                               policy=StopAtXPolicy(opaque))
        assert res == 1

    def get_interpreter(self, codes, always_inline=False):
        ADD = "0"
        JUMP_BACK = "1"
        CALL = "2"
        EXIT = "3"

        if always_inline:
            def can_inline(*args):
                return True
        else:
            def can_inline(code, i):
                code = hlstr(code)
                return not JUMP_BACK in code

        jitdriver = JitDriver(greens = ['code', 'i'], reds = ['n'],
                              can_inline = can_inline)
 
        def interpret(codenum, n, i):
            code = codes[codenum]
            while i < len(code):
                jitdriver.jit_merge_point(n=n, i=i, code=code)
                op = code[i]
                if op == ADD:
                    n += 1
                    i += 1
                elif op == CALL:
                    n = interpret(1, n, 1)
                    i += 1
                elif op == JUMP_BACK:
                    if n > 20:
                        return 42
                    i -= 2
                    jitdriver.can_enter_jit(n=n, i=i, code=code)
                elif op == EXIT:
                    return n
                else:
                    raise NotImplementedError
            return n

        return interpret

    def test_inline(self):
        code = "021"
        subcode = "00"

        codes = [code, subcode]
        f = self.get_interpreter(codes)

        assert self.meta_interp(f, [0, 0, 0], optimizer=OPTIMIZER_SIMPLE) == 42
        self.check_loops(int_add = 1, call = 1)
        assert self.meta_interp(f, [0, 0, 0], optimizer=OPTIMIZER_SIMPLE,
                                inline=True) == 42
        self.check_loops(int_add = 2, call = 0, guard_no_exception = 0)

    def test_inline_jitdriver_check(self):
        code = "021"
        subcode = "100"
        codes = [code, subcode]

        f = self.get_interpreter(codes)

        assert self.meta_interp(f, [0, 0, 0], optimizer=OPTIMIZER_SIMPLE,
                                inline=True) == 42
        self.check_loops(call = 1)

    def test_inline_faulty_can_inline(self):
        code = "021"
        subcode = "301"
        codes = [code, subcode]

        f = self.get_interpreter(codes, always_inline=True)

        try:
            self.meta_interp(f, [0, 0, 0], optimizer=OPTIMIZER_SIMPLE,
                             inline=True)
        except CannotInlineCanEnterJit:
            pass
        else:
            py.test.fail("DID NOT RAISE")

    def test_guard_failure_in_inlined_function(self):
        from pypy.rpython.annlowlevel import hlstr
        def p(code, pc):
            code = hlstr(code)
            return "%s %d %s" % (code, pc, code[pc])
        def c(code, pc):
            return "l" not in hlstr(code)
        myjitdriver = JitDriver(greens=['code', 'pc'], reds=['n'],
                                get_printable_location=p, can_inline=c)
        def f(code, n):
            pc = 0
            while pc < len(code):

                myjitdriver.jit_merge_point(n=n, code=code, pc=pc)
                op = code[pc]
                if op == "-":
                    n -= 1
                elif op == "c":
                    n = f("---i---", n)
                elif op == "i":
                    if n % 5 == 1:
                        return n
                elif op == "l":
                    if n > 0:
                        myjitdriver.can_enter_jit(n=n, code=code, pc=0)
                        pc = 0
                        continue
                else:
                    assert 0
                pc += 1
            return n
        def main(n):
            return f("c-l", n)
        print main(100)
        res = self.meta_interp(main, [100], optimizer=OPTIMIZER_SIMPLE, inline=True)
        assert res == 0

    def test_guard_failure_and_then_exception_in_inlined_function(self):
        from pypy.rpython.annlowlevel import hlstr
        def p(code, pc):
            code = hlstr(code)
            return "%s %d %s" % (code, pc, code[pc])
        def c(code, pc):
            return "l" not in hlstr(code)
        myjitdriver = JitDriver(greens=['code', 'pc'], reds=['n', 'flag'],
                                get_printable_location=p, can_inline=c)
        def f(code, n):
            pc = 0
            flag = False
            while pc < len(code):

                myjitdriver.jit_merge_point(n=n, code=code, pc=pc, flag=flag)
                op = code[pc]
                if op == "-":
                    n -= 1
                elif op == "c":
                    try:
                        n = f("---ir---", n)
                    except Exception:
                        return n
                elif op == "i":
                    if n < 200:
                        flag = True
                elif op == "r":
                    if flag:
                        raise Exception
                elif op == "l":
                    if n > 0:
                        myjitdriver.can_enter_jit(n=n, code=code, pc=0, flag=flag)
                        pc = 0
                        continue
                else:
                    assert 0
                pc += 1
            return n
        def main(n):
            return f("c-l", n)
        print main(1000)
        res = self.meta_interp(main, [1000], optimizer=OPTIMIZER_SIMPLE, inline=True)
        assert res == main(1000)

    def test_exception_in_inlined_function(self):
        from pypy.rpython.annlowlevel import hlstr
        def p(code, pc):
            code = hlstr(code)
            return "%s %d %s" % (code, pc, code[pc])
        def c(code, pc):
            return "l" not in hlstr(code)
        myjitdriver = JitDriver(greens=['code', 'pc'], reds=['n'],
                                get_printable_location=p, can_inline=c)

        class Exc(Exception):
            pass
        
        def f(code, n):
            pc = 0
            while pc < len(code):

                myjitdriver.jit_merge_point(n=n, code=code, pc=pc)
                op = code[pc]
                if op == "-":
                    n -= 1
                elif op == "c":
                    try:
                        n = f("---i---", n)
                    except Exc:
                        pass
                elif op == "i":
                    if n % 5 == 1:
                        raise Exc
                elif op == "l":
                    if n > 0:
                        myjitdriver.can_enter_jit(n=n, code=code, pc=0)
                        pc = 0
                        continue
                else:
                    assert 0
                pc += 1
            return n
        def main(n):
            return f("c-l", n)
        res = self.meta_interp(main, [100], optimizer=OPTIMIZER_SIMPLE, inline=True)
        assert res == main(100)

    def test_recurse_during_blackholing(self):
        # this passes, if the blackholing shortcut for calls is turned off
        # it fails, it is very delicate in terms of parameters,
        # bridge/loop creation order
        from pypy.rpython.annlowlevel import hlstr
        def p(code, pc):
            code = hlstr(code)
            return "%s %d %s" % (code, pc, code[pc])
        def c(code, pc):
            return "l" not in hlstr(code)
        myjitdriver = JitDriver(greens=['code', 'pc'], reds=['n'],
                                get_printable_location=p, can_inline=c)
        
        def f(code, n):
            pc = 0
            while pc < len(code):

                myjitdriver.jit_merge_point(n=n, code=code, pc=pc)
                op = code[pc]
                if op == "-":
                    n -= 1
                elif op == "c":
                    if n < 70 and n % 3 == 1:
                        n = f("--", n)
                elif op == "l":
                    if n > 0:
                        myjitdriver.can_enter_jit(n=n, code=code, pc=0)
                        pc = 0
                        continue
                else:
                    assert 0
                pc += 1
            return n
        def main(n):
            myjitdriver.set_param('threshold', 3)
            myjitdriver.set_param('trace_eagerness', 5)            
            return f("c-l", n)
        expected = main(100)
        res = self.meta_interp(main, [100], optimizer=OPTIMIZER_SIMPLE, inline=True)
        assert res == expected

    def check_max_trace_length(self, length):
        for loop in get_stats().loops:
            assert len(loop.operations) <= length + 5 # because we only check once per metainterp bytecode
            for op in loop.operations:
                if op.is_guard() and hasattr(op.descr, '_debug_suboperations'):
                    assert len(op.descr._debug_suboperations) <= length + 5

    def test_inline_trace_limit(self):
        myjitdriver = JitDriver(greens=[], reds=['n'])
        def recursive(n):
            if n > 0:
                return recursive(n - 1) + 1
            return 0
        def loop(n):            
            myjitdriver.set_param("threshold", 10)
            pc = 0
            while n:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                n = recursive(n)
                n -= 1
            return n
        TRACE_LIMIT = 66
        res = self.meta_interp(loop, [100], optimizer=OPTIMIZER_SIMPLE, inline=True, trace_limit=TRACE_LIMIT)
        assert res == 0
        self.check_max_trace_length(TRACE_LIMIT)
        self.check_enter_count(15) # maybe
        self.check_aborted_count(7)

    def test_trace_limit_bridge(self):
        def recursive(n):
            if n > 0:
                return recursive(n - 1) + 1
            return 0
        myjitdriver = JitDriver(greens=[], reds=['n'])
        def loop(n):
            myjitdriver.set_param("threshold", 4)
            myjitdriver.set_param("trace_eagerness", 2)
            while n:
                myjitdriver.can_enter_jit(n=n)
                myjitdriver.jit_merge_point(n=n)
                if n % 5 == 0:
                    n -= 1
                if n < 50:
                    n = recursive(n)
                n -= 1
            return n
        TRACE_LIMIT = 20
        res = self.meta_interp(loop, [100], optimizer=OPTIMIZER_SIMPLE, inline=True, trace_limit=TRACE_LIMIT)
        self.check_max_trace_length(TRACE_LIMIT)
        self.check_aborted_count(8)
        self.check_enter_count_at_most(30)

    def test_max_failure_args(self):
        FAILARGS_LIMIT = 10
        jitdriver = JitDriver(greens = [], reds = ['o', 'i', 'n'])

        class A(object):
            def __init__(self, i0, i1, i2, i3, i4, i5, i6, i7, i8, i9):
                self.i0 = i0
                self.i1 = i1
                self.i2 = i2
                self.i3 = i3
                self.i4 = i4
                self.i5 = i5
                self.i6 = i6
                self.i7 = i7
                self.i8 = i8
                self.i9 = i9
                
        
        def loop(n):
            i = 0
            o = A(0, 1, 2, 3, 4, 5, 6, 7, 8, 9)
            while i < n:
                jitdriver.can_enter_jit(o=o, i=i, n=n)
                jitdriver.jit_merge_point(o=o, i=i, n=n)
                o = A(i, i + 1, i + 2, i + 3, i + 4, i + 5,
                      i + 6, i + 7, i + 8, i + 9)
                i += 1
            return o

        res = self.meta_interp(loop, [20], failargs_limit=FAILARGS_LIMIT,
                               listops=True)
        self.check_aborted_count(5)

    def test_max_failure_args_exc(self):
        FAILARGS_LIMIT = 10
        jitdriver = JitDriver(greens = [], reds = ['o', 'i', 'n'])

        class A(object):
            def __init__(self, i0, i1, i2, i3, i4, i5, i6, i7, i8, i9):
                self.i0 = i0
                self.i1 = i1
                self.i2 = i2
                self.i3 = i3
                self.i4 = i4
                self.i5 = i5
                self.i6 = i6
                self.i7 = i7
                self.i8 = i8
                self.i9 = i9
                
        
        def loop(n):
            i = 0
            o = A(0, 1, 2, 3, 4, 5, 6, 7, 8, 9)
            while i < n:
                jitdriver.can_enter_jit(o=o, i=i, n=n)
                jitdriver.jit_merge_point(o=o, i=i, n=n)
                o = A(i, i + 1, i + 2, i + 3, i + 4, i + 5,
                      i + 6, i + 7, i + 8, i + 9)
                i += 1
            raise ValueError

        def main(n):
            try:
                loop(n)
                return 1
            except ValueError:
                return 0

        res = self.meta_interp(main, [20], failargs_limit=FAILARGS_LIMIT,
                               listops=True)
        assert not res
        self.check_aborted_count(5)        

    def test_set_param_inlining(self):
        myjitdriver = JitDriver(greens=[], reds=['n', 'recurse'])
        def loop(n, recurse=False):
            while n:
                myjitdriver.jit_merge_point(n=n, recurse=recurse)
                n -= 1
                if not recurse:
                    loop(10, True)
                    myjitdriver.can_enter_jit(n=n, recurse=recurse)
            return n
        TRACE_LIMIT = 66
 
        def main(inline):
            myjitdriver.set_param("threshold", 10)
            if inline:
                myjitdriver.set_param('inlining', True)
            else:
                myjitdriver.set_param('inlining', False)
            return loop(100)

        res = self.meta_interp(main, [0], optimizer=OPTIMIZER_SIMPLE, trace_limit=TRACE_LIMIT)
        self.check_loops(call=1)

        res = self.meta_interp(main, [1], optimizer=OPTIMIZER_SIMPLE, trace_limit=TRACE_LIMIT)
        self.check_loops(call=0)

    def test_leave_jit_hook(self):
        from pypy.rpython.annlowlevel import hlstr
        def p(code, pc):
            code = hlstr(code)
            return "%s %d %s" % (code, pc, code[pc])
        def c(code, pc):
            return "L" not in hlstr(code)

        def really_leave(frame):
            frame.hookcalled = True

        def leave(code, pc, frame):
            really_leave(frame)

        class ExpectedHook(Exception):
            pass
        class UnexpectedHook(Exception):
            pass

        myjitdriver = JitDriver(greens=['code', 'pc'], reds=['self'],
                                get_printable_location=p, can_inline=c,
                                leave=leave)
        class Frame(object):
            hookcalled = True
            
            def __init__(self, n):
                self.n = n
                self.hookcalled = False
            def f(self, code):
                pc = 0
                while pc < len(code):

                    myjitdriver.jit_merge_point(self=self, code=code, pc=pc)
                    op = code[pc]
                    if op == "-":
                        self.n -= 1
                    elif op == "c":
                        frame = Frame(self.n)
                        self.n = frame.f("---i---")
                        if we_are_jitted():
                            if frame.hookcalled:
                                raise UnexpectedHook
                    elif op == "C":
                        frame = Frame(self.n)
                        self.n = frame.f("cL")
                        if we_are_jitted():
                            if not frame.hookcalled:
                                raise ExpectedHook
                    elif op == "i":
                        if self.n % 5 == 1:
                            return self.n
                    elif op == "l":
                        if self.n > 0:
                            myjitdriver.can_enter_jit(self=self, code=code, pc=0)
                            pc = 0
                            continue
                    elif op == "L":
                        if self.n > 50:
                            myjitdriver.can_enter_jit(self=self, code=code, pc=0)
                            pc = 0
                            continue
                    else:
                        assert 0
                    pc += 1
                return self.n
        def main(n):
            frame = Frame(n)
            return frame.f("C-l")
        res = self.meta_interp(main, [100], optimizer=OPTIMIZER_SIMPLE, inline=True)
        assert res == main(100)

class TestLLtype(RecursiveTests, LLJitMixin):
    pass

class TestOOtype(RecursiveTests, OOJitMixin):
    pass
