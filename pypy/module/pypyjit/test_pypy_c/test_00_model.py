import sys
import types
import subprocess
import py
from lib_pypy import disassembler
from pypy.tool.udir import udir
from pypy.tool import logparser
from pypy.jit.tool.jitoutput import parse_prof
from pypy.module.pypyjit.test_pypy_c.model import Log, find_ids_range, find_ids, \
    LoopWithIds, OpMatcher

class BaseTestPyPyC(object):
    def setup_class(cls):
        if '__pypy__' not in sys.builtin_module_names:
            py.test.skip("must run this test with pypy")
        if not sys.pypy_translation_info['translation.jit']:
            py.test.skip("must give a pypy-c with the jit enabled")
        cls.tmpdir = udir.join('test-pypy-jit')
        cls.tmpdir.ensure(dir=True)

    def setup_method(self, meth):
        self.filepath = self.tmpdir.join(meth.im_func.func_name + '.py')

    def run(self, func_or_src, args=[], import_site=False, **jitopts):
        jitopts.setdefault('threshold', 200)
        src = py.code.Source(func_or_src)
        if isinstance(func_or_src, types.FunctionType):
            funcname = func_or_src.func_name
        else:
            funcname = 'main'
        # write the snippet
        arglist = ', '.join(map(repr, args))
        with self.filepath.open("w") as f:
            # we don't want to see the small bridges created
            # by the checkinterval reaching the limit
            f.write("import sys\n")
            f.write("sys.setcheckinterval(10000000)\n")
            f.write(str(src) + "\n")
            f.write("print %s(%s)\n" % (funcname, arglist))
        #
        # run a child pypy-c with logging enabled
        logfile = self.filepath.new(ext='.log')
        #
        cmdline = [sys.executable]
        if not import_site:
            cmdline.append('-S')
        for key, value in jitopts.iteritems():
            cmdline += ['--jit', '%s=%s' % (key, value)]
        cmdline.append(str(self.filepath))
        #
        print cmdline, logfile
        env={'PYPYLOG': 'jit-log-opt,jit-summary:' + str(logfile)}
        #env={'PYPYLOG': ':' + str(logfile)}
        pipe = subprocess.Popen(cmdline,
                                env=env,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        stdout, stderr = pipe.communicate()
        if stderr.startswith('SKIP:'):
            py.test.skip(stderr)
        assert not stderr
        #
        # parse the JIT log
        rawlog = logparser.parse_log_file(str(logfile))
        rawtraces = logparser.extract_category(rawlog, 'jit-log-opt-')
        log = Log(rawtraces)
        log.result = eval(stdout)
        #
        summaries  = logparser.extract_category(rawlog, 'jit-summary')
        if len(summaries) > 0:
            log.jit_summary = parse_prof(summaries[-1])
        else:
            log.jit_summary = None
        #
        return log

    def run_and_check(self, src, args=[], **jitopts):
        log1 = self.run(src, args, threshold=-1)  # without the JIT
        log2 = self.run(src, args, **jitopts)     # with the JIT
        assert log1.result == log2.result
        # check that the JIT actually ran
        assert len(log2.loops_by_filename(self.filepath)) > 0


class TestLog(object):

    def test_find_ids_range(self):
        def f():
            a = 0 # ID: myline
            return a
        #
        start_lineno = f.func_code.co_firstlineno
        code = disassembler.dis(f)
        ids = find_ids_range(code)
        assert len(ids) == 1
        myline_range = ids['myline']
        assert list(myline_range) == range(start_lineno+1, start_lineno+2)

    def test_find_ids(self):
        def f():
            i = 0
            x = 0
            z = x + 3 # ID: myline
            return z
        #
        code = disassembler.dis(f)
        ids = find_ids(code)
        assert len(ids) == 1
        myline = ids['myline']
        opcodes_names = [opcode.__class__.__name__ for opcode in myline]
        assert opcodes_names == ['LOAD_FAST', 'LOAD_CONST', 'BINARY_ADD', 'STORE_FAST']


class TestOpMatcher(object):

    def match(self, src1, src2, **kwds):
        from pypy.tool.jitlogparser.parser import SimpleParser
        loop = SimpleParser.parse_from_input(src1)
        matcher = OpMatcher(loop.operations, src=src1)
        return matcher.match(src2, **kwds)

    def test_match_var(self):
        match_var = OpMatcher([]).match_var
        assert match_var('v0', 'V0')
        assert not match_var('v0', 'V1')
        assert match_var('v0', 'V0')
        #
        # for ConstPtr, we allow the same alpha-renaming as for variables
        assert match_var('ConstPtr(ptr0)', 'PTR0')
        assert not match_var('ConstPtr(ptr0)', 'PTR1')
        assert match_var('ConstPtr(ptr0)', 'PTR0')
        #
        # for ConstClass, we want the exact matching
        assert match_var('ConstClass(foo)', 'ConstClass(foo)')
        assert not match_var('ConstClass(bar)', 'v1')
        assert not match_var('v2', 'ConstClass(baz)')
        #
        # the var '_' matches everything (but only on the right, of course)
        assert match_var('v0', '_')
        assert match_var('v0', 'V0')
        assert match_var('ConstPtr(ptr0)', '_')
        py.test.raises(AssertionError, "match_var('_', 'v0')")

    def test_parse_op(self):
        res = OpMatcher.parse_op("  a =   int_add(  b,  3 ) # foo")
        assert res == ("int_add", "a", ["b", "3"], None)
        res = OpMatcher.parse_op("guard_true(a)")
        assert res == ("guard_true", None, ["a"], None)
        res = OpMatcher.parse_op("setfield_gc(p0, i0, descr=<foobar>)")
        assert res == ("setfield_gc", None, ["p0", "i0"], "<foobar>")
        res = OpMatcher.parse_op("i1 = getfield_gc(p0, descr=<foobar>)")
        assert res == ("getfield_gc", "i1", ["p0"], "<foobar>")
        res = OpMatcher.parse_op("p0 = force_token()")
        assert res == ("force_token", "p0", [], None)

    def test_exact_match(self):
        loop = """
            [i0]
            i2 = int_add(i0, 1)
            jump(i2)
        """
        expected = """
            i5 = int_add(i2, 1)
            jump(i5, descr=...)
        """
        assert self.match(loop, expected)
        #
        expected = """
            i5 = int_sub(i2, 1)
            jump(i5, descr=...)
        """
        assert not self.match(loop, expected)
        #
        expected = """
            i5 = int_add(i2, 1)
            jump(i5, descr=...)
            extra_stuff(i5)
        """
        assert not self.match(loop, expected)
        #
        expected = """
            i5 = int_add(i2, 1)
            # missing op at the end
        """
        assert not self.match(loop, expected)

    def test_match_descr(self):
        loop = """
            [p0]
            setfield_gc(p0, 1, descr=<foobar>)
        """
        assert self.match(loop, "setfield_gc(p0, 1, descr=<foobar>)")
        assert self.match(loop, "setfield_gc(p0, 1, descr=...)")
        assert self.match(loop, "setfield_gc(p0, 1, descr=<.*bar>)")
        assert not self.match(loop, "setfield_gc(p0, 1)")
        assert not self.match(loop, "setfield_gc(p0, 1, descr=<zzz>)")


    def test_partial_match(self):
        loop = """
            [i0]
            i1 = int_add(i0, 1)
            i2 = int_sub(i1, 10)
            i3 = int_floordiv(i2, 100)
            i4 = int_mul(i1, 1000)
            jump(i4)
        """
        expected = """
            i1 = int_add(0, 1)
            ...
            i4 = int_mul(i1, 1000)
            jump(i4, descr=...)
        """
        assert self.match(loop, expected)

    def test_partial_match_is_non_greedy(self):
        loop = """
            [i0]
            i1 = int_add(i0, 1)
            i2 = int_sub(i1, 10)
            i3 = int_mul(i2, 1000)
            i4 = int_mul(i1, 1000)
            jump(i4, descr=...)
        """
        expected = """
            i1 = int_add(0, 1)
            ...
            _ = int_mul(_, 1000)
            jump(i4, descr=...)
        """
        # this does not match, because the ... stops at the first int_mul, and
        # then the second one does not match
        assert not self.match(loop, expected)

    def test_partial_match_at_the_end(self):
        loop = """
            [i0]
            i1 = int_add(i0, 1)
            i2 = int_sub(i1, 10)
            i3 = int_floordiv(i2, 100)
            i4 = int_mul(i1, 1000)
            jump(i4)
        """
        expected = """
            i1 = int_add(0, 1)
            ...
        """
        assert self.match(loop, expected)

    def test_ignore_opcodes(self):
        loop = """
            [i0]
            i1 = int_add(i0, 1)
            i4 = force_token()
            i2 = int_sub(i1, 10)
            jump(i4)
        """
        expected = """
            i1 = int_add(i0, 1)
            i2 = int_sub(i1, 10)
            jump(i4, descr=...)
        """
        assert self.match(loop, expected, ignore_ops=['force_token'])

    def test_match_dots_in_arguments(self):
        loop = """
            [i0]
            i1 = int_add(0, 1)
            jump(i4, descr=...)
        """
        expected = """
            i1 = int_add(...)
            jump(i4, descr=...)
        """
        assert self.match(loop, expected)


class TestRunPyPyC(BaseTestPyPyC):

    def test_run_function(self):
        def f(a, b):
            return a+b
        log = self.run(f, [30, 12])
        assert log.result == 42

    def test_run_src(self):
        src = """
            def f(a, b):
                return a+b
            def main(a, b):
                return f(a, b)
        """
        log = self.run(src, [30, 12])
        assert log.result == 42

    def test_skip(self):
        import pytest
        def f():
            import sys
            print >> sys.stderr, 'SKIP: foobar'
        #
        raises(pytest.skip.Exception, "self.run(f, [])")

    def test_parse_jitlog(self):
        def f():
            i = 0
            while i < 1003:
                i += 1
            return i
        #
        log = self.run(f)
        assert log.result == 1003
        loops = log.loops_by_filename(self.filepath)
        assert len(loops) == 1
        assert loops[0].filename == self.filepath
        assert not loops[0].is_entry_bridge
        #
        loops = log.loops_by_filename(self.filepath, is_entry_bridge=True)
        assert len(loops) == 1
        assert loops[0].is_entry_bridge
        #
        loops = log.loops_by_filename(self.filepath, is_entry_bridge='*')
        assert len(loops) == 2

    def test_loops_by_id(self):
        def f():
            i = 0
            while i < 1003:
                i += 1 # ID: increment
            return i
        #
        log = self.run(f)
        loop, = log.loops_by_id('increment')
        assert loop.filename == self.filepath
        assert loop.code.co.co_name == 'f'
        #
        ops = loop.allops()
        assert log.opnames(ops) == [
            # this is the actual loop
            'int_lt', 'guard_true', 'int_add',
            # this is the signal checking stuff
            'getfield_raw', 'int_sub', 'setfield_raw', 'int_lt', 'guard_false',
            'jump'
            ]

    def test_ops_by_id(self):
        def f():
            i = 0
            while i < 1003: # ID: cond
                i += 1 # ID: increment
                a = 0  # to make sure that JUMP_ABSOLUTE is not part of the ID
            return i
        #
        log = self.run(f)
        loop, = log.loops_by_id('increment')
        #
        ops = loop.ops_by_id('increment')
        assert log.opnames(ops) == ['int_add']
        #
        ops = loop.ops_by_id('cond')
        # the 'jump' at the end is because the last opcode in the loop
        # coincides with the first, and so it thinks that 'jump' belongs to
        # the id
        assert log.opnames(ops) == ['int_lt', 'guard_true', 'jump']

    def test_ops_by_id_and_opcode(self):
        def f():
            i = 0
            j = 0
            while i < 1003:
                i += 1; j -= 1 # ID: foo
                a = 0  # to make sure that JUMP_ABSOLUTE is not part of the ID
            return i
        #
        log = self.run(f)
        loop, = log.loops_by_id('foo')
        #
        ops = loop.ops_by_id('foo', opcode='INPLACE_ADD')
        assert log.opnames(ops) == ['int_add']
        #
        ops = loop.ops_by_id('foo', opcode='INPLACE_SUBTRACT')
        assert log.opnames(ops) == ['int_sub_ovf', 'guard_no_overflow']
        

    def test_inlined_function(self):
        def f():
            def g(x):
                return x+1 # ID: add
            i = 0
            while i < 1003:
                i = g(i) # ID: call
                a = 0    # to make sure that JUMP_ABSOLUTE is not part of the ID
            return i
        #
        log = self.run(f)
        loop, = log.loops_by_filename(self.filepath)
        call_ops = log.opnames(loop.ops_by_id('call'))
        assert call_ops == ['force_token'] # it does not follow inlining
        #
        add_ops = log.opnames(loop.ops_by_id('add'))
        assert add_ops == ['int_add']
        #
        ops = log.opnames(loop.allops())
        assert ops == [
            # this is the actual loop
            'int_lt', 'guard_true', 'force_token', 'int_add',
            # this is the signal checking stuff
            'getfield_raw', 'int_sub', 'setfield_raw', 'int_lt', 'guard_false',
            'jump'
            ]

    def test_loop_match(self):
        def f():
            i = 0
            while i < 1003:
                i += 1 # ID: increment
            return i
        #
        log = self.run(f)
        loop, = log.loops_by_id('increment')
        assert loop.match("""
            i6 = int_lt(i4, 1003)
            guard_true(i6, descr=...)
            i8 = int_add(i4, 1)
            # signal checking stuff
            i10 = getfield_raw(37212896, descr=<.* pypysig_long_struct.c_value .*>)
            i12 = int_sub(i10, 1)
            setfield_raw(37212896, i12, descr=<.* pypysig_long_struct.c_value .*>)
            i14 = int_lt(i12, 0)
            guard_false(i14, descr=...)
            jump(p0, p1, p2, p3, i8, descr=...)
        """)
        #
        assert loop.match("""
            i6 = int_lt(i4, 1003)
            guard_true(i6, descr=...)
            i8 = int_add(i4, 1)
            --TICK--
            jump(p0, p1, p2, p3, i8, descr=...)
        """)
        #
        assert not loop.match("""
            i6 = int_lt(i4, 1003)
            guard_true(i6)
            i8 = int_add(i5, 1) # variable mismatch
            --TICK--
            jump(p0, p1, p2, p3, i8, descr=...)
        """)

    def test_match_by_id(self):
        def f():
            i = 0
            j = 2000
            while i < 1003:
                i += 1 # ID: increment
                j -= 1 # ID: product
                a = 0  # to make sure that JUMP_ABSOLUTE is not part of the ID
            return i
        #
        log = self.run(f)
        loop, = log.loops_by_id('increment')
        assert loop.match_by_id('increment', """
            i1 = int_add(i0, 1)
        """)
        assert loop.match_by_id('product', """
            i4 = int_sub_ovf(i3, 1)
            guard_no_overflow(descr=...)
        """)

    def test_match_constants(self):
        def f():
            from socket import ntohs
            i = 0
            while i < 1003:
                i += 1
                j = ntohs(1) # ID: ntohs
                a = 0
            return i
        log = self.run(f, import_site=True)
        loop, = log.loops_by_id('ntohs')
        assert loop.match_by_id('ntohs', """
            guard_not_invalidated(descr=...)
            p12 = call(ConstClass(ntohs), 1, descr=...)
            guard_no_exception(descr=...)
        """)
        #
        assert not loop.match_by_id('ntohs', """
            guard_not_invalidated(descr=...)
            p12 = call(ConstClass(foobar), 1, descr=...)
            guard_no_exception(descr=...)
        """)
        
