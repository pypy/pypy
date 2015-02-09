import py
import sys, os, subprocess, types
from rpython.tool.udir import udir


class BaseTestSTM(object):

    HEADER = """
import thread, pypystm

NUM_THREADS = 3

_b_to_go = NUM_THREADS
_b_done = False
_b_lock = thread.allocate_lock()
_b_locks = [thread.allocate_lock() for _i in range(NUM_THREADS)]
for _bl in _b_locks:
    _bl.acquire()

class BarrierThreadsDone(Exception):
    pass

def barrier(tnum, done=False):
    '''Waits until NUM_THREADS call this function, and then returns
    in all these threads at once.'''
    global _b_to_go, _b_done
    _b_lock.acquire()
    if done:
        _b_done = True
    _b_to_go -= 1
    if _b_to_go > 0:
        _b_lock.release()
        _b_locks[tnum].acquire()
    else:
        _b_to_go = NUM_THREADS
        for i in range(NUM_THREADS):
            if i != tnum:
                _b_locks[i].release()
        _b_lock.release()
    if _b_done:
        raise BarrierThreadsDone

def _run(tnum, lock, result, function, args):
    start = pypystm.time()
    try:
        try:
            while True:
                function(*args)
                if pypystm.time() - start >= 3.0:
                    break
        except BarrierThreadsDone:
            pass
        result.append(1)
    finally:
        lock.release()
    while len(result) != NUM_THREADS:
        barrier(tnum, done=True)

def run_in_threads(function, arg_thread_num=False, arg_class=None):
    locks = []
    result = []
    for i in range(NUM_THREADS):
        lock = thread.allocate_lock()
        lock.acquire()
        args = ()
        if arg_thread_num:
            args += (i,)
        if arg_class:
            args += (arg_class(),)
        thread.start_new_thread(_run, (i, lock, result, function, args))
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

    def _execute(self, import_site=False, jit=True):
        cmdline = [sys.executable]
        if not jit:
            cmdline.extend(['--jit', 'off'])
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
        if pipe.returncode > 0:
            raise IOError("subprocess error %d:\n%s" % (pipe.returncode,
                                                        stderr))
        if pipe.returncode < 0:
            raise IOError("subprocess was killed by signal %d" % (
                pipe.returncode,))

    def _parse_log(self):
        from pypy.stm.print_stm_log import StmLog
        return StmLog(str(self.logfile))

    def _check_count_conflicts(self, func_or_src, args=[], **kwds):
        self._write_source(func_or_src, args)
        self._execute(**kwds)
        self.stmlog = self._parse_log()
        self.stmlog.dump()
        count = self.stmlog.get_total_aborts_and_pauses()
        print 'stmlog.get_total_aborts_and_pauses():', count
        return count

    def check_almost_no_conflict(self, *args, **kwds):
        count = self._check_count_conflicts(*args, **kwds)
        assert count < 500

    def check_MANY_conflicts(self, *args, **kwds):
        count = self._check_count_conflicts(*args, **kwds)
        assert count > 20000

    def check_SOME_conflicts(self, *args, **kwds):
        count = self._check_count_conflicts(*args, **kwds)
        assert count > 1000

    def check_conflict_location(self, text):
        first_conflict = self.stmlog.get_conflicts()[0]
        assert first_conflict.get_marker1().rstrip().endswith(text)
