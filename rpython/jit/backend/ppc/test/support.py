from pypy.jit.backend.detect_cpu import getcpuclass
from pypy.jit.metainterp.test import support

class JitPPCMixin(support.LLJitMixin):
    type_system = 'lltype'
    CPUClass = getcpuclass()

    def check_jumps(self, maxcount):
        pass
