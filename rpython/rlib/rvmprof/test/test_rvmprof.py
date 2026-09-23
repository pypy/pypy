import py, os
import pytest
import sys
import time
from rpython.tool.udir import udir
from rpython.rlib import rvmprof
from rpython.translator.c.test.test_genc import compile
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.lltypesystem import rffi, lltype

@pytest.mark.usefixtures('init')
class RVMProfTest(object):

    ENTRY_POINT_ARGS = ()

    class MyCode(object):
        def __init__(self, name='py:code:0:noname'):
            self.name = name

        def get_name(self):
            return self.name

    @pytest.fixture
    def init(self):
        self.register()
        self.rpy_entry_point = compile(self.entry_point, self.ENTRY_POINT_ARGS)

    def register(self):
        rvmprof.register_code_object_class(self.MyCode,
                                           self.MyCode.get_name)


def _build_stripped_so(tmpdir):
    """A shared library with its symbols moved into a sibling debug file
    and linked by .gnu_debuglink, the way a packaged PyPy is built.
    Returns the library path, or None if the binutils are missing."""
    import subprocess
    src = tmpdir.join('debuglink.c')
    src.write("""
    static int stripped_func(int x) { return x * 5; }
    long stripped_func_addr(void) { return (long)stripped_func; }
    """)
    so = tmpdir.join('debuglink.so')
    debug = tmpdir.join('debuglink.so.debug')
    try:
        subprocess.check_call(['gcc', '-shared', '-fPIC', '-g', '-O1',
                               '-o', str(so), str(src)])
        subprocess.check_call(['objcopy', '--only-keep-debug',
                               str(so), str(debug)])
        subprocess.check_call(['objcopy', '--strip-all', str(so)])
        subprocess.check_call(['objcopy', '--add-gnu-debuglink=' + str(debug),
                               str(so)])
    except (OSError, subprocess.CalledProcessError):
        return None
    return so


@pytest.mark.skipif(sys.platform == 'win32', reason='no symbolizer on windows')
def test_resolve_addr(tmpdir):
    import ctypes
    # libbacktrace scans the loaded objects once, when the first
    # resolve_addr call creates its state, so every library this test
    # looks up has to be loaded before that
    stripped_addr = 0
    if sys.platform.startswith('linux'):
        stripped = _build_stripped_so(tmpdir)
        if stripped is not None:
            stripped_lib = ctypes.CDLL(str(stripped))
            stripped_lib.stripped_func_addr.restype = ctypes.c_long
            stripped_addr = stripped_lib.stripped_func_addr()

    # a local symbol, only present in .symtab and invisible to dladdr
    eci = ExternalCompilationInfo(
        post_include_bits=['long hidden_func_addr(void);'],
        separate_module_sources=["""
        static int hidden_func(int x) { return x * 3; }
        RPY_EXTERN long hidden_func_addr(void) {
            return (long)hidden_func;
        }
        """])
    hidden_func_addr = rffi.llexternal('hidden_func_addr', [], lltype.Signed,
                                       compilation_info=eci)
    hidden_addr = hidden_func_addr()

    libc = ctypes.CDLL(None)
    addr = ctypes.cast(libc.malloc, ctypes.c_void_p).value
    name, lineno, srcfile = rvmprof.resolve_addr(addr)
    assert 'malloc' in name
    assert lineno >= 0
    assert 'libc' in srcfile
    assert rvmprof.resolve_addr(1) == ('', 0, '')

    name, lineno, srcfile = rvmprof.resolve_addr(hidden_addr)
    assert name == 'hidden_func'
    assert srcfile.endswith('.so')

    if stripped_addr:
        name, lineno, srcfile = rvmprof.resolve_addr(stripped_addr)
        assert name == 'stripped_func'


class TestExecuteCode(RVMProfTest):

    def entry_point(self):
        res = self.main(self.MyCode(), 5)
        assert res == 42
        return 0

    @rvmprof.vmprof_execute_code("xcode1", lambda self, code, num: code)
    def main(self, code, num):
        print num
        return 42

    def test(self):
        assert self.entry_point() == 0
        assert self.rpy_entry_point() == 0


class TestResultClass(RVMProfTest):

    class A: pass

    @rvmprof.vmprof_execute_code("xcode2", lambda self, num, code: code,
                                 result_class=A)
    def main(self, num, code):
        print num
        return self.A()

    def entry_point(self):
        a = self.main(7, self.MyCode())
        assert isinstance(a, self.A)
        return 0

    def test(self):
        assert self.entry_point() == 0
        assert self.rpy_entry_point() == 0


class TestRegisterCode(RVMProfTest):

    @rvmprof.vmprof_execute_code("xcode1", lambda self, code, num: code)
    def main(self, code, num):
        print num
        return 42

    def entry_point(self):
        code = self.MyCode()
        rvmprof.register_code(code, lambda code: 'some code')
        res = self.main(code, 5)
        assert res == 42
        return 0

    def test(self):
        assert self.entry_point() == 0
        assert self.rpy_entry_point() == 0


def vmprof_accounts_for_lost_samples():
    # A pending SIGPROF/SIGALRM is a single bit, so samples coalesce
    # whenever the process is off the cpu for more than one interval, and
    # the profile has no way to show it. Upstream vmprof needs a format
    # newer than VERSION_TIMESTAMP to fix that.
    from vmprof import reader
    versions = [v for k, v in vars(reader).items() if k.startswith('VERSION_')]
    return max(versions) > reader.VERSION_TIMESTAMP


class RVMProfSamplingTest(RVMProfTest):

    # real_time=0 samples with ITIMER_PROF/SIGPROF, which on macOS saturates
    # somewhere around 100-130 Hz no matter what interval is asked for (at
    # 250 Hz it delivers less than half the signals), so the sample count can
    # never match the cpu time. ITIMER_REAL is better there, so use it and
    # compare the sample count against wall time instead of cpu time.
    REAL_TIME = int(sys.platform == 'darwin')

    # the kernel will deliver SIGPROF at max 250 Hz. See also
    # https://github.com/vmprof/vmprof-python/issues/163
    SAMPLING_INTERVAL = 1/250.0

    @pytest.fixture
    def init(self, tmpdir):
        self.tmpdir = tmpdir
        self.tmpfile = tmpdir.join('profile.vmprof')
        self.tmpfilename = str(self.tmpfile)
        super(RVMProfSamplingTest, self).init()

    ENTRY_POINT_ARGS = (int, float, int)
    def entry_point(self, value, delta_t, memory=0):
        code = self.MyCode('py:code:52:test_enable')
        rvmprof.register_code(code, self.MyCode.get_name)
        fd = os.open(self.tmpfilename, os.O_WRONLY | os.O_CREAT, 0666)
        rvmprof.enable(fd, self.SAMPLING_INTERVAL, memory=memory,
                       real_time=self.REAL_TIME)
        start = time.time()
        cpu_start = os.times()
        res = 0
        while time.time() < start+delta_t:
            res = self.main(code, value)
        cpu_end = os.times()
        end = time.time()
        rvmprof.disable()
        os.close(fd)
        if self.REAL_TIME:
            elapsed = end - start
        else:
            elapsed = (cpu_end[0] + cpu_end[1] - cpu_start[0] - cpu_start[1])
        elapsed_usec = int(elapsed * 1000000.0)
        time_fd = os.open(self.tmpfilename + '.time',
                          os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0666)
        os.write(time_fd, str(elapsed_usec))
        os.close(time_fd)
        return res

    def get_sampled_time(self):
        """The time the timer was measuring while entry_point ran: cpu time
        with ITIMER_PROF, wall time with ITIMER_REAL."""
        with open(self.tmpfilename + '.time') as f:
            return int(f.read()) / 1000000.0

    def approx_equal(self, a, b, tolerance=0.15):
        max_diff = (a+b)/2.0 * tolerance
        return abs(a-b) < max_diff


class TestEnable(RVMProfSamplingTest):

    @rvmprof.vmprof_execute_code("xcode1", lambda self, code, count: code)
    def main(self, code, count):
        s = 0
        for i in range(count):
            # make this complicated so clang does not optimize it to a
            # constant expression
            s = (s + (i << 1)) ^ (s >> 3)
        return s

    def test(self):
        from vmprof import read_profile
        assert self.entry_point(10**4, 0.1, 0) == 17697048
        assert self.tmpfile.check()
        self.tmpfile.remove()
        #
        assert self.rpy_entry_point(10**4, 0.5, 0) == 17697048
        sampled_time = self.get_sampled_time()
        assert self.tmpfile.check()
        prof = read_profile(self.tmpfilename)
        tree = prof.get_tree()
        assert tree.name == 'py:code:52:test_enable'
        if sys.platform == 'darwin' and not vmprof_accounts_for_lost_samples():
            pytest.skip("macOS CI runners lose timer signals")
        assert self.approx_equal(tree.count,
                                 sampled_time/self.SAMPLING_INTERVAL)

    def test_mem(self):
        from vmprof import read_profile
        assert self.rpy_entry_point(10**4, 0.5, 1) == 17697048
        assert self.tmpfile.check()
        prof = read_profile(self.tmpfilename)
        assert prof.profile_memory
        assert all(p[-1] > 0 for p in prof.profiles)


class TestNative(RVMProfSamplingTest):

    @pytest.fixture
    def init(self, tmpdir):
        eci = ExternalCompilationInfo(compile_extra=['-g','-O0', '-Werror'],
                post_include_bits = ['int native_func(int);'],
                separate_module_sources=["""
                RPY_EXTERN int native_func(int d) {
                    int j = 0;
                    if (d > 0) {
                        return native_func(d-1);
                    } else {
                        for (int i = 0; i < 42000; i++) {
                            j += 1;
                        }
                    }
                    return j;
                }
                """])
        self.native_func = rffi.llexternal("native_func", [rffi.INT], rffi.INT,
                                           compilation_info=eci)
        super(TestNative, self).init(tmpdir)

    @rvmprof.vmprof_execute_code("xcode1", lambda self, code, count: code)
    def main(self, code, count):
        code = self.MyCode('py:main:3:main')
        rvmprof.register_code(code, self.MyCode.get_name)
        code = self.MyCode('py:code:7:native_func')
        rvmprof.register_code(code, self.MyCode.get_name)
        if count > 0:
            return self.main(code, count-1)
        else:
            return self.native_func(100)

    def test(self):
        from vmprof import read_profile
        # from vmprof.show import PrettyPrinter
        assert self.rpy_entry_point(3, 0.5, 0) == 42000
        assert self.tmpfile.check()

        prof = read_profile(self.tmpfilename)
        tree = prof.get_tree()
        # p = PrettyPrinter()
        # p._print_tree(tree)
        def walk(tree, symbols):
            symbols.append(tree.name)
            if len(tree.children) == 0:
                return
            for child in tree.children.values():
                walk(child, symbols)
        symbols = []
        walk(tree, symbols)
        not_found = ['py:code:7:native_func']
        for sym in symbols:
            for i,name in enumerate(not_found):
                if sym.startswith(name):
                    del not_found[i]
                    break
        assert not_found == []
