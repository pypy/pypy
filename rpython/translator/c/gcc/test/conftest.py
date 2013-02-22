import py
from rpython.jit.backend import detect_cpu
cpu = detect_cpu.autodetect()
def pytest_runtest_setup(item):
    if cpu not in ('x86', 'x86_64'):
        py.test.skip("x86 directory skipped: cpu is %r" % (cpu,))
