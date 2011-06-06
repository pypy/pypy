from pypy.conftest import gettestobjspace, option
from pypy.tool.udir import udir
import py
from py.test import skip
import sys, os, re
import subprocess

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

        print logfilepath
        env = os.environ.copy()
        env['PYPYLOG'] = ":%s" % (logfilepath,)
        p = subprocess.Popen([self.pypy_c, str(filepath)],
                             env=env, stdout=subprocess.PIPE)
        result, _ = p.communicate()
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


    def test_richards(self):
        self.run_source('''
            import sys; sys.path[:] = %r
            from pypy.translator.goal import richards

            def main():
                return richards.main(iterations = 1)
        ''' % (sys.path,), 7200,
                   ([], 42))


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
