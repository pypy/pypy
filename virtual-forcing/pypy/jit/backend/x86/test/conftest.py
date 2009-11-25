import py
from pypy.jit.backend import detect_cpu

class Directory(py.test.collect.Directory):
    def collect(self):
        cpu = detect_cpu.autodetect()
        if cpu != 'i386':
            py.test.skip("x86 directory skipped: cpu is %r" % (cpu,))
        return super(Directory, self).collect()
