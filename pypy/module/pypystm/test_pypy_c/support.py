import py
import sys, os, subprocess, types
from rpython.tool.udir import udir


class BaseTestSTM(object):

    HEADER = """
import thread, pypystm

def _run(lock, result, function):
    start = pypystm.time()
    try:
        while True:
            function()
            if pypystm.time() - start >= 3.0:
                break
        result.append(1)
    finally:
        lock.release()

def run_in_threads(function):
    locks = []
    result = []
    for i in range(3):
        lock = thread.allocate_lock()
        lock.acquire()
        thread.start_new_thread(_run, (lock, result, function))
        locks.append(lock)
    for lock in locks:
        lock._py3k_acquire(timeout=30)
    if len(result) < len(locks):
        raise Exception("not all threads completed successfully")
"""

    def setup_class(cls):
        if '__pypy__' not in sys.builtin_module_names:
            py.test.skip("must run this test with pypy")
        try:
            import pypystm
        except ImportError:
            py.test.skip("must give a pypy-c with stm enabled")
        cls.tmpdir = udir.join('test-pypy-stm')
        cls.tmpdir.ensure(dir=True)

    def setup_method(self, meth):
        self.filepath = self.tmpdir.join(meth.im_func.func_name + '.py')
        self.logfile = self.filepath.new(ext='.log')

    def _write_source(self, func_or_src, args=[]):
        src = py.code.Source(func_or_src)
        if isinstance(func_or_src, types.FunctionType):
            funcname = func_or_src.func_name
        else:
            funcname = 'main'
        arglist = ', '.join(map(repr, args))
        with self.filepath.open("w") as f:
            f.write(self.HEADER)
            f.write(str(src) + '\n')
            f.write("print %s(%s)\n" % (funcname, arglist))

    def _execute(self, import_site=False):
        cmdline = [sys.executable]
        if not import_site:
            cmdline.append('-S')
        cmdline.append(str(self.filepath))
        env = os.environ.copy()
        env['PYPYSTM'] = str(self.logfile)
        #
        pipe = subprocess.Popen(cmdline,
                                env=env,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        stdout, stderr = pipe.communicate()
        if getattr(pipe, 'returncode', 0) < 0:
            raise IOError("subprocess was killed by signal %d" % (
                pipe.returncode,))

    def _parse_log(self):
        from pypy.stm.print_stm_log import StmLog
        return StmLog(str(self.logfile))

    def check_almost_no_conflict(self, func_or_src, args=[]):
        self._write_source(func_or_src, args)
        self._execute()
        stmlog = self._parse_log()
        assert stmlog.get_total_aborts_and_pauses() < 1000
