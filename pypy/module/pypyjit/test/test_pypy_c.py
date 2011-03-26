from pypy.conftest import gettestobjspace, option
from pypy.tool.udir import udir
import py
from py.test import skip
import sys, os, re

class BytecodeTrace(list):
    def get_opnames(self, prefix=""):
        return [op.getopname() for op in self
                    if op.getopname().startswith(prefix)]

    def __repr__(self):
        return "%s%s" % (self.bytecode, list.__repr__(self))

ZERO_OP_BYTECODES = [
    'POP_TOP',
    'ROT_TWO',
    'ROT_THREE',
    'DUP_TOP',
    'ROT_FOUR',
    'NOP',
    'DUP_TOPX',
    'LOAD_CONST',
    'JUMP_FORWARD',
    #'JUMP_ABSOLUTE' in theory, but contains signals stuff
    #'LOAD_FAST' should be here, but currently needs a guard for nonzeroness
    'STORE_FAST',
    ]


r_bridge = re.compile(r"bridge out of Guard (\d+)")

def from_entry_bridge(text, allparts):
    firstline = text.splitlines()[0]
    if 'entry bridge' in firstline:
        return True
    match = r_bridge.search(firstline)
    if match:
        search = '<Guard' + match.group(1) + '>'
        for part in allparts:
            if search in part:
                break
        else:
            raise AssertionError, "%s not found??" % (search,)
        return from_entry_bridge(part, allparts)
    return False

def test_from_entry_bridge():
    assert from_entry_bridge(
        "# Loop 4 : entry bridge with 31 ops\n[p0, etc", [])
    assert not from_entry_bridge(
        "# Loop 1 : loop with 31 ops\n[p0, p1, etc", [])
    assert not from_entry_bridge(
        "# bridge out of Guard 5 with 24 ops\n[p0, p1, etc",
        ["# Loop 1 : loop with 31 ops\n"
             "[p0, p1]\n"
             "guard_stuff(descr=<Guard5>)\n"])
    assert from_entry_bridge(
        "# bridge out of Guard 5 with 24 ops\n[p0, p1, etc",
        ["# Loop 1 : entry bridge with 31 ops\n"
             "[p0, p1]\n"
             "guard_stuff(descr=<Guard5>)\n"])
    assert not from_entry_bridge(
        "# bridge out of Guard 51 with 24 ops\n[p0, p1, etc",
        ["# Loop 1 : loop with 31 ops\n"
             "[p0, p1]\n"
             "guard_stuff(descr=<Guard5>)\n",
         "# bridge out of Guard 5 with 13 ops\n"
             "[p0, p1]\n"
             "guard_other(p1, descr=<Guard51>)\n"])
    assert from_entry_bridge(
        "# bridge out of Guard 51 with 24 ops\n[p0, p1, etc",
        ["# Loop 1 : entry bridge with 31 ops\n"
             "[p0, p1]\n"
             "guard_stuff(descr=<Guard5>)\n",
         "# bridge out of Guard 5 with 13 ops\n"
             "[p0, p1]\n"
             "guard_other(p1, descr=<Guard51>)\n"])


class PyPyCJITTests(object):
    def run_source(self, source, expected_max_ops, *testcases, **kwds):
        assert isinstance(expected_max_ops, int)
        threshold = kwds.pop('threshold', 3)
        self.count_debug_merge_point = \
                                     kwds.pop('count_debug_merge_point', True)
        if kwds:
            raise TypeError, 'Unsupported keyword arguments: %s' % kwds.keys()
        source = py.code.Source(source)
        filepath = self.tmpdir.join('case%d.py' % self.counter)
        logfilepath = filepath.new(ext='.log')
        self.__class__.counter += 1
        f = filepath.open('w')
        print >> f, source
        # some support code...
        print >> f, py.code.Source("""
            import sys
            # we don't want to see the small bridges created
            # by the checkinterval reaching the limit
            sys.setcheckinterval(10000000)
            try: # make the file runnable by CPython
                import pypyjit
                pypyjit.set_param(threshold=%d)
            except ImportError:
                pass

            def check(args, expected):
                #print >> sys.stderr, 'trying:', args
                result = main(*args)
                #print >> sys.stderr, 'got:', repr(result)
                assert result == expected
                assert type(result) is type(expected)
        """ % threshold)
        for testcase in testcases * 2:
            print >> f, "check(%r, %r)" % testcase
        print >> f, "print 'OK :-)'"
        f.close()

        if sys.platform.startswith('win'):
            py.test.skip("XXX this is not Windows-friendly")
        print logfilepath
        child_stdout = os.popen('PYPYLOG=":%s" "%s" "%s"' % (
            logfilepath, self.pypy_c, filepath), 'r')
        result = child_stdout.read()
        child_stdout.close()
        assert result
        if result.strip().startswith('SKIP:'):
            py.test.skip(result.strip())
        assert result.splitlines()[-1].strip() == 'OK :-)'
        self.parse_loops(logfilepath)
        self.print_loops()
        print logfilepath
        if self.total_ops > expected_max_ops:
            assert 0, "too many operations: got %d, expected maximum %d" % (
                self.total_ops, expected_max_ops)
        return result

    def parse_loops(self, opslogfile):
        from pypy.tool import logparser
        assert opslogfile.check()
        log = logparser.parse_log_file(str(opslogfile))
        parts = logparser.extract_category(log, 'jit-log-opt-')
        self.rawloops = [part for part in parts
                         if not from_entry_bridge(part, parts)]
        self.loops, self.sliced_loops, self.total_ops = \
                                           self.parse_rawloops(self.rawloops)
        self.check_0_op_bytecodes()
        self.rawentrybridges = [part for part in parts
                                if from_entry_bridge(part, parts)]
        _, self.sliced_entrybridge, _ = \
                                    self.parse_rawloops(self.rawentrybridges)

        from pypy.jit.tool.jitoutput import parse_prof
        summaries  = logparser.extract_category(log, 'jit-summary')
        if len(summaries) > 0:
            self.jit_summary = parse_prof(summaries[-1])
        else:
            self.jit_summary = None
        

    def parse_rawloops(self, rawloops):
        from pypy.jit.tool.oparser import parse
        loops = [parse(part, no_namespace=True) for part in rawloops]
        sliced_loops = [] # contains all bytecodes of all loops
        total_ops = 0
        for loop in loops:
            for op in loop.operations:
                if op.getopname() == "debug_merge_point":
                    sliced_loop = BytecodeTrace()
                    sliced_loop.bytecode = op.getarg(0)._get_str().rsplit(" ", 1)[1]
                    sliced_loops.append(sliced_loop)
                    if self.count_debug_merge_point:
                        total_ops += 1
                else:
                    sliced_loop.append(op)
                    total_ops += 1
        return loops, sliced_loops, total_ops

    def check_0_op_bytecodes(self):
        for bytecodetrace in self.sliced_loops:
            if bytecodetrace.bytecode not in ZERO_OP_BYTECODES:
                continue
            assert not bytecodetrace

    def get_by_bytecode(self, name, from_entry_bridge=False):
        if from_entry_bridge:
            sliced_loops = self.sliced_entrybridge
        else:
            sliced_loops = self.sliced_loops
        return [ops for ops in sliced_loops if ops.bytecode == name]

    def print_loops(self):
        for rawloop in self.rawloops:
            print
            print '@' * 79
            print
            print rawloop.rstrip()
        print
        print '@' * 79

    def test_f1(self):
        self.run_source('''
            def main(n):
                "Arbitrary test function."
                i = 0
                x = 1
                while i<n:
                    j = 0   #ZERO
                    while j<=i:
                        j = j + 1
                        x = x + (i&j)
                    i = i + 1
                return x
        ''', 220,
                   ([2117], 1083876708))

    def test_factorial(self):
        self.run_source('''
            def main(n):
                r = 1
                while n > 1:
                    r *= n
                    n -= 1
                return r
        ''', 28,
                   ([5], 120),
                    ([25], 15511210043330985984000000L))

    def test_factorialrec(self):
        self.run_source('''
            def main(n):
                if n > 1:
                    return n * main(n-1)
                else:
                    return 1
        ''', 0,
                   ([5], 120),
                    ([25], 15511210043330985984000000L))

    def test_richards(self):
        self.run_source('''
            import sys; sys.path[:] = %r
            from pypy.translator.goal import richards

            def main():
                return richards.main(iterations = 1)
        ''' % (sys.path,), 7200,
                   ([], 42))

    def test_simple_call(self):
        self.run_source('''
            OFFSET = 0
            def f(i):
                return i + 1 + OFFSET
            def main(n):
                i = 0
                while i < n+OFFSET:
                    i = f(f(i))
                return i
        ''', 98,
                   ([20], 20),
                    ([31], 32))
        ops = self.get_by_bytecode("LOAD_GLOBAL", True)
        assert len(ops) == 5
        assert ops[0].get_opnames() == ["guard_value",
                                        "getfield_gc", "guard_value",
                                        "getfield_gc", "guard_isnull",
                                        "getfield_gc", "guard_nonnull_class"]
        # the second getfield on the same globals is quicker
        assert ops[1].get_opnames() == ["getfield_gc", "guard_nonnull_class"]
        assert not ops[2] # second LOAD_GLOBAL of the same name folded away
        # LOAD_GLOBAL of the same name but in different function partially
        # folded away
        # XXX could be improved
        assert ops[3].get_opnames() == ["guard_value",
                                        "getfield_gc", "guard_isnull"]
        assert not ops[4]
        ops = self.get_by_bytecode("CALL_FUNCTION", True)
        assert len(ops) == 2
        for i, bytecode in enumerate(ops):
            if i == 0:
                assert "call(getexecutioncontext)" in str(bytecode)
            else:
                assert not bytecode.get_opnames("call")
            assert not bytecode.get_opnames("new")
            assert len(bytecode.get_opnames("guard")) <= 10

        ops = self.get_by_bytecode("LOAD_GLOBAL")
        assert len(ops) == 5
        for bytecode in ops:
            assert not bytecode

        ops = self.get_by_bytecode("CALL_FUNCTION")
        assert len(ops) == 2
        for bytecode in ops:
            assert len(bytecode) <= 1
        

    def test_method_call(self):
        self.run_source('''
            class A(object):
                def __init__(self, a):
                    self.a = a
                def f(self, i):
                    return self.a + i
            def main(n):
                i = 0
                a = A(1)
                while i < n:
                    x = a.f(i)
                    i = a.f(x)
                return i
        ''', 93,
                   ([20], 20),
                    ([31], 32))
        ops = self.get_by_bytecode("LOOKUP_METHOD", True)
        assert len(ops) == 2
        assert not ops[0].get_opnames("call")
        assert not ops[0].get_opnames("new")
        assert len(ops[0].get_opnames("guard")) <= 3
        assert not ops[1] # second LOOKUP_METHOD folded away

        ops = self.get_by_bytecode("LOOKUP_METHOD")
        assert not ops[0] # first LOOKUP_METHOD folded away
        assert not ops[1] # second LOOKUP_METHOD folded away

        ops = self.get_by_bytecode("CALL_METHOD", True)
        assert len(ops) == 2
        for i, bytecode in enumerate(ops):
            if i == 0:
                assert "call(getexecutioncontext)" in str(bytecode)
            else:
                assert not bytecode.get_opnames("call")
            assert not bytecode.get_opnames("new")
            assert len(bytecode.get_opnames("guard")) <= 6
        assert len(ops[1]) < len(ops[0])

        ops = self.get_by_bytecode("CALL_METHOD")
        assert len(ops) == 2
        assert len(ops[0]) <= 1
        assert len(ops[1]) <= 1
        
        ops = self.get_by_bytecode("LOAD_ATTR", True)
        assert len(ops) == 2
        # With mapdict, we get fast access to (so far) the 5 first
        # attributes, which means it is done with only the following
        # operations.  (For the other attributes there is additionally
        # a getarrayitem_gc.)
        assert ops[0].get_opnames() == ["getfield_gc",
                                        "guard_nonnull_class"]
        assert not ops[1] # second LOAD_ATTR folded away

        ops = self.get_by_bytecode("LOAD_ATTR")
        assert not ops[0] # first LOAD_ATTR folded away
        assert not ops[1] # second LOAD_ATTR folded away

    def test_static_classmethod_call(self):
        self.run_source('''
            class A(object):
                @classmethod
                def f(cls, i):
                    return i + (cls is A) + 1

                @staticmethod
                def g(i):
                    return i - 1

            def main(n):
                i = 0
                a = A()
                while i < n:
                    x = a.f(i)
                    i = a.g(x)
                return i
        ''', 106,
                   ([20], 20),
                   ([31], 31))
        ops = self.get_by_bytecode("LOOKUP_METHOD")
        assert len(ops) == 2
        assert not ops[0].get_opnames("call")
        assert not ops[0].get_opnames("new")
        assert len(ops[0].get_opnames("guard")) <= 2
        assert len(ops[0].get_opnames("getfield")) <= 4
        assert not ops[1] # second LOOKUP_METHOD folded away

    def test_default_and_kw(self):
        self.run_source('''
            def f(i, j=1):
                return i + j
            def main(n):
                i = 0
                while i < n:
                    i = f(f(i), j=1)
                return i
        ''', 100,
                   ([20], 20),
                   ([31], 32))
        ops = self.get_by_bytecode("CALL_FUNCTION")
        assert len(ops) == 2
        for i, bytecode in enumerate(ops):
            assert not bytecode.get_opnames("call")
            assert not bytecode.get_opnames("new")
        assert len(ops[0].get_opnames("guard")) <= 14
        assert len(ops[1].get_opnames("guard")) <= 3

        ops = self.get_by_bytecode("CALL_FUNCTION", True)
        assert len(ops) == 2
        for i, bytecode in enumerate(ops):
            if i == 0:
                assert "call(getexecutioncontext)" in str(bytecode)
            else:
                assert not bytecode.get_opnames("call")
            assert not bytecode.get_opnames("new")
        assert len(ops[0].get_opnames("guard")) <= 14
        assert len(ops[1].get_opnames("guard")) <= 3

    def test_kwargs(self):
        self.run_source('''
            d = {}

            def g(**args):
                return len(args)

            def main(x):
                s = 0
                d = {}
                for i in range(x):
                    s += g(**d)
                    d[str(i)] = i
                    if i % 100 == 99:
                        d = {}
                return s
        ''', 100000, ([100], 4950),
                    ([1000], 49500),
                    ([10000], 495000),
                    ([100000], 4950000))
        assert len(self.rawloops)  + len(self.rawentrybridges) == 4
        op, = self.get_by_bytecode("CALL_FUNCTION_KW")
        # XXX a bit too many guards, but better than before
        assert len(op.get_opnames("guard")) <= 12

    def test_stararg_virtual(self):
        self.run_source('''
            d = {}

            def g(*args):
                return len(args)
            def h(a, b, c):
                return c

            def main(x):
                s = 0
                for i in range(x):
                    l = [i, x, 2]
                    s += g(*l)
                    s += h(*l)
                    s += g(i, x, 2)
                for i in range(x):
                    l = [x, 2]
                    s += g(i, *l)
                    s += h(i, *l)
                return s
        ''', 100000, ([100], 1300),
                    ([1000], 13000),
                    ([10000], 130000),
                    ([100000], 1300000))
        assert len(self.loops) == 2
        ops = self.get_by_bytecode("CALL_FUNCTION_VAR")
        assert len(ops) == 4
        for op in ops:
            assert len(op.get_opnames("new")) == 0
            assert len(op.get_opnames("call_may_force")) == 0

        ops = self.get_by_bytecode("CALL_FUNCTION")
        for op in ops:
            assert len(op.get_opnames("new")) == 0
            assert len(op.get_opnames("call_may_force")) == 0

    def test_stararg(self):
        self.run_source('''
            d = {}

            def g(*args):
                return args[-1]
            def h(*args):
                return len(args)

            def main(x):
                s = 0
                l = []
                i = 0
                while i < x:
                    l.append(1)
                    s += g(*l)
                    i = h(*l)
                return s
        ''', 100000, ([100], 100),
                     ([1000], 1000),
                     ([2000], 2000),
                     ([4000], 4000))
        assert len(self.loops) == 1
        ops = self.get_by_bytecode("CALL_FUNCTION_VAR")
        for op in ops:
            assert len(op.get_opnames("new_with_vtable")) == 0
            assert len(op.get_opnames("call_may_force")) == 0

    def test_virtual_instance(self):
        self.run_source('''
            class A(object):
                pass
            def main(n):
                i = 0
                while i < n:
                    a = A()
                    assert isinstance(a, A)
                    assert not isinstance(a, int)
                    a.x = 2
                    i = i + a.x
                return i
        ''', 69,
                   ([20], 20),
                   ([31], 32))

        callA, callisinstance1, callisinstance2 = (
                self.get_by_bytecode("CALL_FUNCTION"))
        assert not callA.get_opnames("call")
        assert not callA.get_opnames("new")
        assert len(callA.get_opnames("guard")) <= 2
        assert not callisinstance1.get_opnames("call")
        assert not callisinstance1.get_opnames("new")
        assert len(callisinstance1.get_opnames("guard")) <= 2
        # calling isinstance on a builtin type gives zero guards
        # because the version_tag of a builtin type is immutable
        assert not len(callisinstance1.get_opnames("guard"))


        bytecode, = self.get_by_bytecode("STORE_ATTR")
        assert bytecode.get_opnames() == []

    def test_load_attr(self):
        self.run_source('''
            class A(object):
                pass
            a = A()
            a.x = 2
            def main(n):
                i = 0
                while i < n:
                    i = i + a.x
                return i
        ''', 41,
                   ([20], 20),
                   ([31], 32))

        load, = self.get_by_bytecode("LOAD_ATTR")
        # 1 guard_value for the class
        # 1 guard_value for the version_tag
        # 1 guard_value for the structure
        # 1 guard_nonnull_class for the result since it is used later
        assert len(load.get_opnames("guard")) <= 4

    def test_mixed_type_loop(self):
        self.run_source('''
            class A(object):
                pass
            def main(n):
                i = 0.0
                j = 2
                while i < n:
                    i = j + i
                return i, type(i) is float
        ''', 35,
                   ([20], (20, True)),
                   ([31], (32, True)))

        bytecode, = self.get_by_bytecode("BINARY_ADD")
        assert not bytecode.get_opnames("call")
        assert not bytecode.get_opnames("new")
        assert len(bytecode.get_opnames("guard")) <= 2

    def test_call_builtin_function(self):
        self.run_source('''
            class A(object):
                pass
            def main(n):
                i = 2
                l = []
                while i < n:
                    i += 1
                    l.append(i)
                return i, len(l)
        ''', 39,
                   ([20], (20, 18)),
                   ([31], (31, 29)))

        bytecode, = self.get_by_bytecode("CALL_METHOD")
        assert len(bytecode.get_opnames("new_with_vtable")) == 1 # the forcing of the int
        assert len(bytecode.get_opnames("call")) == 1 # the call to append
        assert len(bytecode.get_opnames("guard")) == 1 # guard for guard_no_exception after the call
        bytecode, = self.get_by_bytecode("CALL_METHOD", True)
        assert len(bytecode.get_opnames("guard")) == 2 # guard for profiling disabledness + guard_no_exception after the call

    def test_range_iter(self):
        self.run_source('''
            def g(n):
                return range(n)

            def main(n):
                s = 0
                for i in range(n):
                    s += g(n)[i]
                return s
        ''', 143, ([1000], 1000 * 999 / 2))
        bytecode, = self.get_by_bytecode("BINARY_SUBSCR", True)
        assert bytecode.get_opnames("guard") == [
            "guard_false",   # check that the index is >= 0
            "guard_false",   # check that the index is lower than the current length
            ]
        bytecode, _ = self.get_by_bytecode("FOR_ITER", True) # second bytecode is the end of the loop
        assert bytecode.get_opnames("guard") == [
            "guard_value",
            "guard_class",   # check the class of the iterator
            "guard_nonnull", # check that the iterator is not finished
            "guard_isnull",  # check that the range list is not forced
            "guard_false",   # check that the index is lower than the current length
            ]

        bytecode, = self.get_by_bytecode("BINARY_SUBSCR")
        assert bytecode.get_opnames("guard") == [
            "guard_false",   # check that the index is >= 0
            "guard_false",   # check that the index is lower than the current length
            ]
        bytecode, _ = self.get_by_bytecode("FOR_ITER") # second bytecode is the end of the loop
        assert bytecode.get_opnames("guard") == [
            "guard_false",   # check that the index is lower than the current length
            ]

    def test_exception_inside_loop_1(self):
        self.run_source('''
            def main(n):
                while n:
                    try:
                        raise ValueError
                    except ValueError:
                        pass
                    n -= 1
                return n
        ''', 33,
                  ([30], 0))

        bytecode, = self.get_by_bytecode("SETUP_EXCEPT")
        #assert not bytecode.get_opnames("new")   -- currently, we have
        #               new_with_vtable(pypy.interpreter.pyopcode.ExceptBlock)
        bytecode, = self.get_by_bytecode("RAISE_VARARGS")
        assert not bytecode.get_opnames("new")
        bytecode, = self.get_by_bytecode("COMPARE_OP")
        assert not bytecode.get_opnames()

    def test_exception_inside_loop_2(self):
        self.run_source('''
            def g(n):
                raise ValueError(n)
            def f(n):
                g(n)
            def main(n):
                while n:
                    try:
                        f(n)
                    except ValueError:
                        pass
                    n -= 1
                return n
        ''', 51,
                  ([30], 0))

        bytecode, = self.get_by_bytecode("RAISE_VARARGS")
        assert not bytecode.get_opnames("new")
        bytecode, = self.get_by_bytecode("COMPARE_OP")
        assert len(bytecode.get_opnames()) <= 2    # oois, guard_true

    def test_chain_of_guards(self):
        self.run_source('''
        class A(object):
            def method_x(self):
                return 3

        l = ["x", "y"]

        def main(arg):
            sum = 0
            a = A()
            i = 0
            while i < 2000:
                name = l[arg]
                sum += getattr(a, 'method_' + name)()
                i += 1
            return sum
        ''', 3000, ([0], 2000*3))
        assert len(self.loops) == 1

    def test_getattr_with_dynamic_attribute(self):
        self.run_source('''
        class A(object):
            pass

        l = ["x", "y"]

        def main(arg):
            sum = 0
            a = A()
            a.a1 = 0
            a.a2 = 0
            a.a3 = 0
            a.a4 = 0
            a.a5 = 0 # workaround, because the first five attributes need a promotion
            a.x = 1
            a.y = 2
            i = 0
            while i < 2000:
                name = l[i % 2]
                sum += getattr(a, name)
                i += 1
            return sum
        ''', 3000, ([0], 3000))
        assert len(self.loops) == 1

    def test_blockstack_virtualizable(self):
        self.run_source('''
        from pypyjit import residual_call

        def main():
            i = 0
            while i < 100:
                try:
                    residual_call(len, [])
                except:
                    pass
                i += 1
            return i
        ''', 1000, ([], 100))
        bytecode, = self.get_by_bytecode("CALL_FUNCTION")
        # we allocate virtual ref and frame, we don't want block
        assert len(bytecode.get_opnames('new_with_vtable')) == 2

    def test_import_in_function(self):
        self.run_source('''
        def main():
            i = 0
            while i < 100:
                from sys import version
                i += 1
            return i
        ''', 100, ([], 100))
        bytecode, = self.get_by_bytecode('IMPORT_NAME')
        bytecode2, = self.get_by_bytecode('IMPORT_FROM')
        assert len(bytecode.get_opnames('call')) == 2 # split_chr and list_pop
        assert len(bytecode2.get_opnames('call')) == 0

    def test_arraycopy_disappears(self):
        self.run_source('''
        def main():
            i = 0
            while i < 100:
                t = (1, 2, 3, i + 1)
                t2 = t[:]
                del t
                i = t2[3]
                del t2
            return i
        ''', 40, ([], 100))
        bytecode, = self.get_by_bytecode('BINARY_SUBSCR')
        assert len(bytecode.get_opnames('new_array')) == 0

    def test_overflow_checking(self):
        startvalue = sys.maxint - 2147483647
        self.run_source('''
        def main():
            def f(a,b):
                if a < 0: return -1
                return a-b
            total = %d
            for i in range(100000):
                total += f(i, 5)
            return total
        ''' % startvalue, 170, ([], startvalue + 4999450000L))

    def test_boolrewrite_invers(self):
        for a, b, res, ops in (('2000', '2000', 20001000, 51),
                               ( '500',  '500', 15001500, 81),
                               ( '300',  '600', 16001700, 83),
                               (   'a',    'b', 16001700, 89),
                               (   'a',    'a', 13001700, 85)):

            self.run_source('''
            def main():
                sa = 0
                a = 300
                b = 600
                for i in range(1000):
                    if i < %s: sa += 1
                    else: sa += 2
                    if i >= %s: sa += 10000
                    else: sa += 20000
                return sa
            '''%(a, b), ops, ([], res))

    def test_boolrewrite_reflex(self):
        for a, b, res, ops in (('2000', '2000', 10001000, 51),
                               ( '500',  '500', 15001500, 81),
                               ( '300',  '600', 14001700, 83),
                               (   'a',    'b', 14001700, 89),
                               (   'a',    'a', 17001700, 85)):

            self.run_source('''
            def main():
                sa = 0
                a = 300
                b = 600
                for i in range(1000):
                    if i < %s: sa += 1
                    else: sa += 2
                    if %s > i: sa += 10000
                    else: sa += 20000
                return sa
            '''%(a, b), ops, ([], res))


    def test_boolrewrite_correct_invers(self):
        def opval(i, op, a):
            if eval('%d %s %d' % (i, op, a)): return 1
            return 2

        ops = ('<', '>', '<=', '>=', '==', '!=')        
        for op1 in ops:
            for op2 in ops:
                for a,b in ((500, 500), (300, 600)):
                    res = 0
                    res += opval(a-1, op1, a) * (a)
                    res += opval(  a, op1, a) 
                    res += opval(a+1, op1, a) * (1000 - a - 1)
                    res += opval(b-1, op2, b) * 10000 * (b)
                    res += opval(  b, op2, b) * 10000 
                    res += opval(b+1, op2, b) * 10000 * (1000 - b - 1)

                    self.run_source('''
                    def main():
                        sa = 0
                        for i in range(1000):
                            if i %s %d: sa += 1
                            else: sa += 2
                            if i %s %d: sa += 10000
                            else: sa += 20000
                        return sa
                    '''%(op1, a, op2, b), 83, ([], res))

                    self.run_source('''
                    def main():
                        sa = 0
                        i = 0.0
                        while i < 250.0:
                            if i %s %f: sa += 1
                            else: sa += 2
                            if i %s %f: sa += 10000
                            else: sa += 20000
                            i += 0.25
                        return sa
                    '''%(op1, float(a)/4.0, op2, float(b)/4.0), 156, ([], res))
                    

    def test_boolrewrite_correct_reflex(self):
        def opval(i, op, a):
            if eval('%d %s %d' % (i, op, a)): return 1
            return 2

        ops = ('<', '>', '<=', '>=', '==', '!=')        
        for op1 in ops:
            for op2 in ops:
                for a,b in ((500, 500), (300, 600)):
                    res = 0
                    res += opval(a-1, op1, a) * (a)
                    res += opval(  a, op1, a) 
                    res += opval(a+1, op1, a) * (1000 - a - 1)
                    res += opval(b, op2, b-1) * 10000 * (b)
                    res += opval(b, op2,   b) * 10000
                    res += opval(b, op2, b+1) * 10000 * (1000 - b - 1)

                    self.run_source('''
                    def main():
                        sa = 0
                        for i in range(1000):
                            if i %s %d: sa += 1
                            else: sa += 2
                            if %d %s i: sa += 10000
                            else: sa += 20000
                        return sa
                    '''%(op1, a, b, op2), 83, ([], res))

                    self.run_source('''
                    def main():
                        sa = 0
                        i = 0.0
                        while i < 250.0:
                            if i %s %f: sa += 1
                            else: sa += 2
                            if %f %s i: sa += 10000
                            else: sa += 20000
                            i += 0.25
                        return sa
                    '''%(op1, float(a)/4.0, float(b)/4.0, op2), 156, ([], res))

    def test_boolrewrite_ptr(self):
        # XXX this test is way too imprecise in what it is actually testing
        # it should count the number of guards instead
        compares = ('a == b', 'b == a', 'a != b', 'b != a', 'a == c', 'c != b')
        for e1 in compares:
            for e2 in compares:
                a, b, c = 1, 2, 3
                if eval(e1): res = 752 * 1 
                else: res = 752 * 2 
                if eval(e2): res += 752 * 10000 
                else: res += 752 * 20000 
                a = b
                if eval(e1): res += 248 * 1
                else: res += 248 * 2
                if eval(e2): res += 248 * 10000
                else: res += 248 * 20000


                if 'c' in e1 or 'c' in e2:
                    n = 337
                else:
                    n = 215

                print
                print 'Test:', e1, e2, n, res
                self.run_source('''
                class tst(object):
                    pass
                def main():
                    a = tst()
                    b = tst()
                    c = tst()
                    sa = 0
                    for i in range(1000):
                        if %s: sa += 1
                        else: sa += 2
                        if %s: sa += 10000
                        else: sa += 20000
                        if i > 750: a = b
                    return sa
                '''%(e1, e2), n, ([], res))

    def test_array_sum(self):
        for tc, maxops in zip('bhilBHILfd', (38,) * 6 + (40, 40, 41, 38)):
            res = 19352859
            if tc == 'L':
                res = long(res)
            elif tc in 'fd':
                res = float(res)
            elif tc == 'I' and sys.maxint == 2147483647:
                res = long(res)
                # note: in CPython we always get longs here, even on 64-bits

            self.run_source('''
            from array import array

            def main():
                img = array("%s", range(127) * 5) * 484
                l, i = 0, 0
                while i < 640 * 480:
                    l += img[i]
                    i += 1
                return l
            ''' % tc, maxops, ([], res))

    def test_array_sum_char(self):
        self.run_source('''
            from array import array

            def main():
                img = array("c", "Hello") * 130 * 480
                l, i = 0, 0
                while i < 640 * 480:
                    l += ord(img[i])
                    i += 1
                return l
            ''', 60, ([], 30720000))

    def test_array_sum_unicode(self):
        self.run_source('''
            from array import array

            def main():
                img = array("u", u"Hello") * 130 * 480
                l, i = 0, 0
                while i < 640 * 480:
                    if img[i] == u"l":
                        l += 1
                    i += 1
                return l
            ''', 65, ([], 122880))

    def test_array_intimg(self):
        # XXX this test is way too imprecise in what it is actually testing
        # it should count the number of guards instead
        for tc, maxops in zip('ilILd', (67, 67, 70, 70, 61)):
            print
            print '='*65
            print '='*20, 'running test for tc=%r' % (tc,), '='*20
            res = 73574560
            if tc == 'L':
                res = long(res)
            elif tc in 'fd':
                res = float(res)
            elif tc == 'I' and sys.maxint == 2147483647:
                res = long(res)
                # note: in CPython we always get longs here, even on 64-bits

            self.run_source('''
            from array import array

            def main(tc):
                img = array(tc, range(3)) * (350 * 480)
                intimg = array(tc, (0,)) * (640 * 480)
                l, i = 0, 640
                while i < 640 * 480:
                    l = l + img[i]
                    intimg[i] = (intimg[i-640] + l) 
                    i += 1
                return intimg[i - 1]
            ''', maxops, ([tc], res))

    def test_unpackiterable(self):
        self.run_source('''
        from array import array

        def main():
            i = 0
            t = array('l', (1, 2))
            while i < 2000:
                a, b = t
                i += 1
            return 3

        ''', 100, ([], 3))
        bytecode, = self.get_by_bytecode("UNPACK_SEQUENCE")
        # we allocate virtual ref and frame, we don't want block
        assert len(bytecode.get_opnames('call_may_force')) == 0
        

    def test_intbound_simple(self):
        ops = ('<', '>', '<=', '>=', '==', '!=')
        nbr = (3, 7)
        for o1 in ops:
            for o2 in ops:
                for n1 in nbr:
                    for n2 in nbr:
                        src = '''
                        def f(i):
                            a, b = 3, 3
                            if i %s %d:
                                a = 0
                            else:
                                a = 1
                            if i %s %d:
                                b = 0
                            else:
                                b = 1
                            return a + b * 2

                        def main():
                            res = [0] * 4
                            idx = []
                            for i in range(15):
                                idx.extend([i] * 1500)
                            for i in idx:
                                res[f(i)] += 1
                            return res

                        ''' % (o1, n1, o2, n2)

                        exec(str(py.code.Source(src)))
                        res = [0] * 4
                        for i in range(15):
                            res[f(i)] += 1500
                        self.run_source(src, 268, ([], res))

    def test_intbound_addsub_mix(self):
        tests = ('i > 4', 'i > 2', 'i + 1 > 2', '1 + i > 4',
                 'i - 1 > 1', '1 - i > 1', '1 - i < -3',
                 'i == 1', 'i == 5', 'i != 1', '-2 * i < -4')
        for t1 in tests:
            for t2 in tests:
                print t1, t2
                src = '''
                def f(i):
                    a, b = 3, 3
                    if %s:
                        a = 0
                    else:
                        a = 1
                    if %s:
                        b = 0
                    else:
                        b = 1
                    return a + b * 2

                def main():
                    res = [0] * 4
                    idx = []
                    for i in range(15):
                        idx.extend([i] * 1500)
                    for i in idx:
                        res[f(i)] += 1
                    return res

                ''' % (t1, t2)

                exec(str(py.code.Source(src)))
                res = [0] * 4
                for i in range(15):
                    res[f(i)] += 1500
                self.run_source(src, 280, ([], res))

    def test_intbound_gt(self):
        self.run_source('''
        def main():
            i, a, b = 0, 0, 0
            while i < 2000:
                if i > -1:
                    a += 1
                if i > -2:
                    b += 1
                i += 1
            return (a, b)
        ''', 48, ([], (2000, 2000)))

    def test_intbound_sub_lt(self):
        self.run_source('''
        def main():
            i, a, b = 0, 0, 0
            while i < 2000:
                if i - 10 < 1995:
                    a += 1
                i += 1
            return (a, b)
        ''', 38, ([], (2000, 0)))

    def test_intbound_addsub_ge(self):
        self.run_source('''
        def main():
            i, a, b = 0, 0, 0
            while i < 2000:
                if i + 5 >= 5:
                    a += 1
                if i - 1 >= -1:
                    b += 1
                i += 1
            return (a, b)
        ''', 56, ([], (2000, 2000)))

    def test_intbound_addmul_ge(self):
        self.run_source('''
        def main():
            i, a, b = 0, 0, 0
            while i < 2000:
                if i + 5 >= 5:
                    a += 1
                if 2 * i >= 0:
                    b += 1
                i += 1
            return (a, b)
        ''', 53, ([], (2000, 2000)))

    def test_intbound_eq(self):
        self.run_source('''
        def main(a):
            i, s = 0, 0
            while i < 1500:
                if a == 7:
                    s += a + 1
                elif i == 10:
                    s += i
                else:
                    s += 1
                i += 1
            return s
        ''', 69, ([7], 12000), ([42], 1509), ([10], 1509))
        
    def test_intbound_mul(self):
        self.run_source('''
        def main(a):
            i, s = 0, 0
            while i < 1500:
                assert i >= 0
                if 2 * i < 30000:
                    s += 1
                else:
                    s += a
                i += 1
            return s
        ''', 43, ([7], 1500))
        
    def test_assert(self):
        self.run_source('''
        def main(a):
            i, s = 0, 0
            while i < 1500:
                assert a == 7
                s += a + 1
                i += 1
            return s
        ''', 38, ([7], 8*1500))
        
    def test_zeropadded(self):
        self.run_source('''
        from array import array
        class ZeroPadded(array):
            def __new__(cls, l):
                self = array.__new__(cls, 'd', range(l))
                return self

            def __getitem__(self, i):
                if i < 0 or i >= self.__len__():
                    return 0
                return array.__getitem__(self, i)


        def main():
            buf = ZeroPadded(2000)
            i = 10
            sa = 0
            while i < 2000 - 10:
                sa += buf[i-2] + buf[i-1] + buf[i] + buf[i+1] + buf[i+2]
                i += 1
            return sa

        ''', 232, ([], 9895050.0))

    def test_circular(self):
        self.run_source('''
        from array import array
        class Circular(array):
            def __new__(cls):
                self = array.__new__(cls, 'd', range(256))
                return self
            def __getitem__(self, i):
                # assert self.__len__() == 256 (FIXME: does not improve)
                return array.__getitem__(self, i & 255)

        def main():
            buf = Circular()
            i = 10
            sa = 0
            while i < 2000 - 10:
                sa += buf[i-2] + buf[i-1] + buf[i] + buf[i+1] + buf[i+2]
                i += 1
            return sa

        ''', 170, ([], 1239690.0))

    def test_min_max(self):
        self.run_source('''
        def main():
            i=0
            sa=0
            while i < 2000: 
                sa+=min(max(i, 3000), 4000)
                i+=1
            return sa
        ''', 51, ([], 2000*3000))

    def test_silly_max(self):
        self.run_source('''
        def main():
            i=2
            sa=0
            while i < 2000: 
                sa+=max(*range(i))
                i+=1
            return sa
        ''', 125, ([], 1997001))

    def test_iter_max(self):
        self.run_source('''
        def main():
            i=2
            sa=0
            while i < 2000: 
                sa+=max(range(i))
                i+=1
            return sa
        ''', 88, ([], 1997001))

    def test__ffi_call(self):
        from pypy.rlib.test.test_libffi import get_libm_name
        libm_name = get_libm_name(sys.platform)
        out = self.run_source('''
        def main():
            try:
                from _ffi import CDLL, types
            except ImportError:
                sys.stdout.write('SKIP: cannot import _ffi')
                return 0

            libm = CDLL('%(libm_name)s')
            pow = libm.getfunc('pow', [types.double, types.double],
                               types.double)
            print pow.getaddr()
            i = 0
            res = 0
            while i < 2000:
                res += pow(2, 3)
                i += 1
            return res
        ''' % locals(),
                              76, ([], 8.0*2000), threshold=1000)
        pow_addr = int(out.splitlines()[0])
        ops = self.get_by_bytecode('CALL_FUNCTION')
        assert len(ops) == 2 # we get two loops, because of specialization
        call_function = ops[0]
        last_ops = [op.getopname() for op in call_function[-5:]]
        assert last_ops == ['force_token',
                            'setfield_gc',
                            'call_may_force',
                            'guard_not_forced',
                            'guard_no_exception']
        call = call_function[-3]
        assert call.getarg(0).value == pow_addr
        assert call.getarg(1).value == 2.0
        assert call.getarg(2).value == 3.0

    def test_xor(self):
        values = (-4, -3, -2, -1, 0, 1, 2, 3, 4)
        for a in values:
            for b in values:
                if a^b >= 0:
                    r = 2000
                else:
                    r = 0
                ops = 46
                
                self.run_source('''
                def main(a, b):
                    i = sa = 0
                    while i < 2000:
                        if a > 0: # Specialises the loop
                            pass
                        if b > 1:
                            pass
                        if a^b >= 0:
                            sa += 1
                        i += 1
                    return sa
                ''', ops, ([a, b], r))
        
    def test_shift(self):
        from sys import maxint
        maxvals = (-maxint-1, -maxint, maxint-1, maxint)
        for a in (-4, -3, -2, -1, 0, 1, 2, 3, 4) + maxvals:
            for b in (0, 1, 2, 31, 32, 33, 61, 62, 63):
                r = 0
                if (a >> b) >= 0:
                    r += 2000
                if (a << b) > 2:
                    r += 20000000
                if abs(a) < 10 and b < 5:
                    ops = 13
                else:
                    ops = 29

                self.run_source('''
                def main(a, b):
                    i = sa = 0
                    while i < 2000:
                        if a > 0: # Specialises the loop
                            pass
                        if b < 2 and b > 0:
                            pass
                        if (a >> b) >= 0:
                            sa += 1
                        if (a << b) > 2:
                            sa += 10000
                        i += 1
                    return sa
                ''', ops, ([a, b], r), count_debug_merge_point=False)

    def test_revert_shift(self):
        from sys import maxint
        tests = []
        for a in (1, 4, 8, 100):
            for b in (-10, 10, -201, 201, -maxint/3, maxint/3):
                for c in (-10, 10, -maxint/3, maxint/3):
                    tests.append(([a, b, c], long(4000*(a+b+c))))
        self.run_source('''
        def main(a, b, c):
            from sys import maxint
            i = sa = 0
            while i < 2000:
                if 0 < a < 10: pass
                if -100 < b < 100: pass
                if -maxint/2 < c < maxint/2: pass
                sa += (a<<a)>>a
                sa += (b<<a)>>a
                sa += (c<<a)>>a
                sa += (a<<100)>>100
                sa += (b<<100)>>100
                sa += (c<<100)>>100
                i += 1
            return long(sa)
        ''', 93, count_debug_merge_point=False, *tests)
        
    def test_division_to_rshift(self):
        avalues = ('a', 'b', 7, -42, 8)
        bvalues = ['b'] + range(-10, 0) + range(1,10)
        code = ''
        a1, b1, res1 = 10, 20, 0
        a2, b2, res2 = 10, -20, 0
        a3, b3, res3 = -10, -20, 0
        def dd(a, b, aval, bval):
            m = {'a': aval, 'b': bval}
            if not isinstance(a, int):
                a=m[a]
            if not isinstance(b, int):
                b=m[b]
            return a/b
        for a in avalues:
            for b in bvalues:
                code += '                sa += %s / %s\n' % (a, b)
                res1 += dd(a, b, a1, b1)
                res2 += dd(a, b, a2, b2)
                res3 += dd(a, b, a3, b3)
        # The purpose of this test is to check that we get
        # the correct results, not really to count operations.
        self.run_source('''
        def main(a, b):
            i = sa = 0
            while i < 2000:
%s                
                i += 1
            return sa
        ''' % code, sys.maxint, ([a1, b1], 2000 * res1),
                                ([a2, b2], 2000 * res2),
                                ([a3, b3], 2000 * res3))

    def test_mod(self):
        avalues = ('a', 'b', 7, -42, 8)
        bvalues = ['b'] + range(-10, 0) + range(1,10)
        code = ''
        a1, b1, res1 = 10, 20, 0
        a2, b2, res2 = 10, -20, 0
        a3, b3, res3 = -10, -20, 0
        def dd(a, b, aval, bval):
            m = {'a': aval, 'b': bval}
            if not isinstance(a, int):
                a=m[a]
            if not isinstance(b, int):
                b=m[b]
            return a % b
        for a in avalues:
            for b in bvalues:
                code += '                sa += %s %% %s\n' % (a, b)
                res1 += dd(a, b, a1, b1)
                res2 += dd(a, b, a2, b2)
                res3 += dd(a, b, a3, b3)
        # The purpose of this test is to check that we get
        # the correct results, not really to count operations.
        self.run_source('''
        def main(a, b):
            i = sa = 0
            while i < 2000:
                if a > 0: pass
                if 1 < b < 2: pass
%s
                i += 1
            return sa
        ''' % code, sys.maxint, ([a1, b1], 2000 * res1),
                                ([a2, b2], 2000 * res2),
                                ([a3, b3], 2000 * res3))

    def test_dont_trace_every_iteration(self):
        self.run_source('''
        def main(a, b):
            i = sa = 0
            while i < 200:
                if a > 0: pass
                if 1 < b < 2: pass
                sa += a % b
                i += 1
            return sa
        ''', 22,  ([10, 20], 200 * (10 % 20)),
                 ([-10, -20], 200 * (-10 % -20)),
                        count_debug_merge_point=False)
        assert self.jit_summary.tracing_no == 2
    def test_id_compare_optimization(self):
        # XXX: lower the instruction count, 35 is the old value.
        self.run_source("""
        class A(object):
            pass
        def main():
            i = 0
            a = A()
            while i < 5:
                if A() != a:
                    pass
                i += 1
        """, 35, ([], None))
        _, compare = self.get_by_bytecode("COMPARE_OP")
        assert "call" not in compare.get_opnames()

class AppTestJIT(PyPyCJITTests):
    def setup_class(cls):
        if not option.runappdirect:
            py.test.skip("meant only for pypy-c")
        # the next line skips stuff if the pypy-c is not a jit build
        cls.space = gettestobjspace(usemodules=['pypyjit'])
        cls.tmpdir = udir.join('pypy-jit')
        cls.tmpdir.ensure(dir=1)
        cls.counter = 0
        cls.pypy_c = sys.executable

class TestJIT(PyPyCJITTests):
    def setup_class(cls):
        if option.pypy_c is None:
            py.test.skip("pass --pypy!")
        if not has_info(option.pypy_c, 'translation.jit'):
            py.test.skip("must give a pypy-c with the jit enabled")
        cls.tmpdir = udir.join('pypy-jit')
        cls.tmpdir.ensure(dir=1)
        cls.counter = 0
        cls.pypy_c = option.pypy_c


def test_interface_residual_call():
    space = gettestobjspace(usemodules=['pypyjit'])
    space.appexec([], """():
        import pypyjit
        def f(*args, **kwds):
            return (args, kwds)
        res = pypyjit.residual_call(f, 4, x=6)
        assert res == ((4,), {'x': 6})
    """)


def has_info(pypy_c, option):
    g = os.popen('"%s" --info' % pypy_c, 'r')
    lines = g.readlines()
    g.close()
    if not lines:
        raise ValueError("cannot execute %r" % pypy_c)
    for line in lines:
        line = line.strip()
        if line.startswith(option + ':'):
            line = line[len(option)+1:].strip()
            if line == 'True':
                return True
            elif line == 'False':
                return False
            else:
                return line
    raise ValueError(option + ' not found in ' + pypy_c)
