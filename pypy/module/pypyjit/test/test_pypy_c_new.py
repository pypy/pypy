import py, sys, re
import subprocess
from lib_pypy import disassembler
from pypy.tool.udir import udir
from pypy.tool import logparser

class Trace(object):
    pass

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

    def parse_out(self, out):
        out = out.strip("\n")
        if out == 'None':
            return None
        try:
            return int(out)
        except ValueError:
            return out

    def parse_func(self, func):
        # find lines such as # LOOP <name> is in a line
        code = disassembler.dis(func)
        result = {}
        for i, line in enumerate(py.code.Source(func)):
            m = re.search('# LOOP (\w+)', line)
            if m:
                name = m.group(1)
                result[name] = []
                for opcode in code.opcodes:
                    no = opcode.lineno - func.func_code.co_firstlineno
                    if i - 1 <= no <= i + 1:
                        result[name].append(opcode)
        return result
    
    def run(self, func):
        with self.filepath.open("w") as f:
            f.write(str(py.code.Source(func)) + "\n")
            f.write("print %s()\n" % func.func_name)
        logfile = self.filepath.new(ext='.log')
        pipe = subprocess.Popen([sys.executable, str(self.filepath)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                env={'PYPYLOG': "jit-log-opt,jit-summary:" + str(logfile)})
        pipe.wait()
        stderr = pipe.stderr.read()
        assert not stderr
        res = self.parse_out(pipe.stdout.read())
        bytecodes = self.parse_func(func)
        assert res == func()
        log = logparser.parse_log_file(str(logfile))
        parts = logparser.extract_category(log, 'jit-log-opt-')
        import pdb;pdb.set_trace()
        log.xxx
        return Trace()

class TestInfrastructure(BaseTestPyPyC):
    def test_parse_func(self):
        def f():
            i = 0
            x = 0
            # LOOP my_loop
            z = x + 3
            return z

        res = self.parse_func(f)
        assert len(res) == 1
        my_loop = res['my_loop']
        opcodes_names = [opcode.__class__.__name__ for opcode in my_loop]
        assert opcodes_names == ['LOAD_CONST', 'STORE_FAST', 'LOAD_FAST',
                                 'LOAD_CONST', 'BINARY_ADD', 'STORE_FAST']

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
