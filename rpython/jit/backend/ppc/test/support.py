from rpython.jit.backend.detect_cpu import getcpuclass
from rpython.jit.metainterp.test import support

class JitPPCMixin(support.LLJitMixin):
    type_system = 'lltype'
    CPUClass = getcpuclass()

    def check_jumps(self, maxcount):
        pass
