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
    def run_source(self, source, expected_max_ops, *testcases):
        assert isinstance(expected_max_ops, int)
        source = py.code.Source(source)
        filepath = self.tmpdir.join('case%d.py' % self.counter)
        logfilepath = filepath.new(ext='.log')
        self.__class__.counter += 1
        f = filepath.open('w')
        print >> f, source
        # some support code...
        print >> f, py.code.Source("""
            import sys
            try: # make the file runnable by CPython
                import pypyjit
                pypyjit.set_param(threshold=3)
            except ImportError:
                pass

            def check(args, expected):
                print >> sys.stderr, 'trying:', args
                result = main(*args)
                print >> sys.stderr, 'got:', repr(result)
                assert result == expected
                assert type(result) is type(expected)
        """)
        for testcase in testcases * 2:
            print >> f, "check(%r, %r)" % testcase
        print >> f, "print 'OK :-)'"
        f.close()

        if sys.platform.startswith('win'):
            py.test.skip("XXX this is not Windows-friendly")
        child_stdout = os.popen('PYPYLOG=":%s" "%s" "%s"' % (
            logfilepath, self.pypy_c, filepath), 'r')
        result = child_stdout.read()
        child_stdout.close()
        assert result
        assert result.splitlines()[-1].strip() == 'OK :-)'
        self.parse_loops(logfilepath)
        self.print_loops()
        if self.total_ops > expected_max_ops:
            assert 0, "too many operations: got %d, expected maximum %d" % (
                self.total_ops, expected_max_ops)

    def parse_loops(self, opslogfile):
        from pypy.jit.metainterp.test.oparser import parse
        from pypy.tool import logparser
        assert opslogfile.check()
        log = logparser.parse_log_file(str(opslogfile))
        parts = logparser.extract_category(log, 'jit-log-opt-')
        # skip entry bridges, they can contain random things
        self.loops = [parse(part, no_namespace=True) for part in parts
                          if not from_entry_bridge(part, parts)]
        self.sliced_loops = [] # contains all bytecodes of all loops
        self.total_ops = 0
        for loop in self.loops:
            self.total_ops += len(loop.operations)
            for op in loop.operations:
                if op.getopname() == "debug_merge_point":
                    sliced_loop = BytecodeTrace()
                    sliced_loop.bytecode = op.args[0]._get_str().rsplit(" ", 1)[1]
                    self.sliced_loops.append(sliced_loop)
                else:
                    sliced_loop.append(op)
        self.check_0_op_bytecodes()

    def check_0_op_bytecodes(self):
        for bytecodetrace in self.sliced_loops:
            if bytecodetrace.bytecode not in ZERO_OP_BYTECODES:
                continue
            assert not bytecodetrace

    def get_by_bytecode(self, name):
        return [ops for ops in self.sliced_loops if ops.bytecode == name]

    def print_loops(self):
        for loop in self.loops:
            print
            print '@' * 79
            print
            for op in loop.operations:
                print op
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
                    ([20], 2432902008176640000L))

    def test_factorialrec(self):
        self.run_source('''
            def main(n):
                if n > 1:
                    return n * main(n-1)
                else:
                    return 1
        ''', 0,
                   ([5], 120),
                    ([20], 2432902008176640000L))

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
        ''', 96,
                   ([20], 20),
                    ([31], 32))
        ops = self.get_by_bytecode("LOAD_GLOBAL")
        assert len(ops) == 5
        assert ops[0].get_opnames() == ["getfield_gc", "guard_value",
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
        ops = self.get_by_bytecode("CALL_FUNCTION")
        assert len(ops) == 2
        for i, bytecode in enumerate(ops):
            if i == 0:
                assert "call(getexecutioncontext)" in str(bytecode)
            else:
                assert not bytecode.get_opnames("call")
            assert not bytecode.get_opnames("new")
            assert len(bytecode.get_opnames("guard")) <= 10

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
        ''', 92,
                   ([20], 20),
                    ([31], 32))
        ops = self.get_by_bytecode("LOOKUP_METHOD")
        assert len(ops) == 2
        assert not ops[0].get_opnames("call")
        assert not ops[0].get_opnames("new")
        assert len(ops[0].get_opnames("guard")) <= 7
        assert not ops[1] # second LOOKUP_METHOD folded away

        ops = self.get_by_bytecode("CALL_METHOD")
        assert len(ops) == 2
        for i, bytecode in enumerate(ops):
            if i == 0:
                assert "call(getexecutioncontext)" in str(bytecode)
            else:
                assert not bytecode.get_opnames("call")
            assert not bytecode.get_opnames("new")
            assert len(bytecode.get_opnames("guard")) <= 9
        assert len(ops[1]) < len(ops[0])

        ops = self.get_by_bytecode("LOAD_ATTR")
        assert len(ops) == 2
        assert ops[0].get_opnames() == ["getfield_gc", "getarrayitem_gc",
                                        "guard_nonnull_class"]
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
        ''', 105,
                   ([20], 20),
                   ([31], 31))
        ops = self.get_by_bytecode("LOOKUP_METHOD")
        assert len(ops) == 2
        assert not ops[0].get_opnames("call")
        assert not ops[0].get_opnames("new")
        assert len(ops[0].get_opnames("guard")) <= 7
        assert len(ops[0].get_opnames("getfield")) < 6
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
        assert len(self.loops) == 2
        op, = self.get_by_bytecode("CALL_FUNCTION_KW")
        # XXX a bit too many guards, but better than before
        assert len(op.get_opnames("guard")) <= 10

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
        ''', 67,
                   ([20], 20),
                   ([31], 32))

        callA, callisinstance1, callisinstance2 = (
                self.get_by_bytecode("CALL_FUNCTION"))
        assert not callA.get_opnames("call")
        assert not callA.get_opnames("new")
        assert len(callA.get_opnames("guard")) <= 8
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
        bytecode, = self.get_by_bytecode("BINARY_SUBSCR")
        assert bytecode.get_opnames("guard") == [
            "guard_isnull",  # check that the range list is not forced
            "guard_false",   # check that the index is >= 0
            "guard_false",   # check that the index is lower than the current length
            ]
        bytecode, _ = self.get_by_bytecode("FOR_ITER") # second bytecode is the end of the loop
        assert bytecode.get_opnames("guard") == [
            "guard_class",   # check the class of the iterator
            "guard_nonnull", # check that the iterator is not finished
            "guard_isnull",  # check that the range list is not forced
            "guard_false",   # check that the index is lower than the current length
            ]
 
    def test_exception_inside_loop_1(self):
        py.test.skip("exceptions: in-progress")
        self.run_source('''
            def main(n):
                while n:
                    try:
                        raise ValueError
                    except ValueError:
                        pass
                    n -= 1
                return n
        ''',
                  ([30], 0))

        bytecode, = self.get_by_bytecode("SETUP_EXCEPT")
        #assert not bytecode.get_opnames("new")   -- currently, we have
        #               new_with_vtable(pypy.interpreter.pyopcode.ExceptBlock)
        bytecode, = self.get_by_bytecode("RAISE_VARARGS")
        assert not bytecode.get_opnames("new")
        bytecode, = self.get_by_bytecode("COMPARE_OP")
        assert not bytecode.get_opnames()

    def test_exception_inside_loop_2(self):
        py.test.skip("exceptions: in-progress")
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
        ''',
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

    def test_blockstack_virtualizable(self):
        self.run_source('''
        def g(k):
            s = 0
            for i in range(k, k+2):
                s += 1
            return s

        def main():
            i = 0
            while i < 100:
                try:
                    g(i)
                except:
                    pass
                i += 1
            return i
        ''', 1000, ([], 100))
        bytecode, = self.get_by_bytecode("CALL_FUNCTION")
        # we allocate virtual ref and frame, we don't want block
        assert len(bytecode.get_opnames('new_with_vtable')) == 2

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
