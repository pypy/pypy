import py
from pypy.jit.backend import detect_cpu

cpu = detect_cpu.autodetect()
def pytest_runtest_setup(item):
    if cpu != 'x86':
        py.test.skip("x86 directory skipped: cpu is %r" % (cpu,))
    
