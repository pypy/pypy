import py
from pypy.jit.backend import detect_cpu

class Module(py.test.collect.Module):
    def collect(self):
        cpu = detect_cpu.autodetect()
        if cpu != 'x86':
            py.test.skip("x86 directory skipped: cpu is %r" % (cpu,))
        return super(Module, self).collect()
