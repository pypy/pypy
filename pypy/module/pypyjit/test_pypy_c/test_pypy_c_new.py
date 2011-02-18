import py, sys, re
import subprocess
from lib_pypy import disassembler
from pypy.tool.udir import udir
from pypy.tool import logparser
from pypy.module.pypyjit.test_pypy_c.model import Log

        


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

    
    def run(self, func, threshold=1000):
        # write the snippet
        with self.filepath.open("w") as f:
            f.write(str(py.code.Source(func)) + "\n")
            f.write("%s()\n" % func.func_name)
        #
        # run a child pypy-c with logging enabled
        logfile = self.filepath.new(ext='.log')
        env={'PYPYLOG': 'jit-log-opt,jit-summary:' + str(logfile)}
        cmdline = [sys.executable,
                   '--jit', 'threshold=%d' % threshold,
                   str(self.filepath)]
        pipe = subprocess.Popen(cmdline,
                                env=env,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        pipe.wait()
        stderr = pipe.stderr.read()
        stdout = pipe.stdout.read()
        assert not stderr
        #
        # parse the JIT log
        rawlog = logparser.parse_log_file(str(logfile))
        rawtraces = logparser.extract_category(rawlog, 'jit-log-opt-')
        log = Log(func, rawtraces)
        return log

class TestInfrastructure(BaseTestPyPyC):

    def test_parse_jitlog(self):
        def f():
            i = 0
            while i < 1003: # default threshold is 10
                i += 1 # ID: increment
            return i
        #
        trace = self.run(f)


    def test_full(self):
        py.test.skip('in-progress')
        def f():
            i = 0
            while i < 1003:
                # LOOP one
                i += 1

        trace = self.run(f)
        loop = trace.get_loops('one')
        loop.get_bytecode(3, 'LOAD_FAST').match('''
        int_add
        guard_true
        ''')
        loop.get_bytecode(4, 'LOAD_CONST').match_stats(
            guard='3', call='1-2', call_may_force='0'
        )
        # this would make operations that are "costly" obligatory to pass
        # like new
        loo.get_bytecode(5, 'INPLACE_ADD').match_stats(
            allocs='5-10'
            )

class TestPyPyCNew(BaseTestPyPyC):
    pass
