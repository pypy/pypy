import py
from rpython.tool.udir import udir
from rpython.jit.backend.arm.detect import detect_arch_version

cpuinfo = "Processor : ARMv%d-compatible processor rev 7 (v6l)"""
cpuinfo2 = """processor       : 0
vendor_id       : GenuineIntel
cpu family      : 6
model           : 23
model name      : Intel(R) Core(TM)2 Duo CPU     E8400  @ 3.00GHz
stepping        : 10
microcode       : 0xa07
cpu MHz         : 2997.000
cache size      : 6144 KB
physical id     : 0
siblings        : 2
core id         : 0
cpu cores       : 2
apicid          : 0
initial apicid  : 0
fpu             : yes
fpu_exception   : yes
cpuid level     : 13
wp              : yes
flags           : fpu vme ...
bogomips        : 5993.08
clflush size    : 64
cache_alignment : 64
address sizes   : 36 bits physical, 48 bits virtual
power management:
"""

def write_cpuinfo(info):
    filepath = udir.join('get_arch_version')
    filepath.write(info)
    return str(filepath)


def test_detect_arch_version():
    # currently supported cases
    for i in (6, 7, ):
        filepath = write_cpuinfo(cpuinfo % i)
        assert detect_arch_version(filepath) == i
    # unsupported cases
    assert detect_arch_version(write_cpuinfo(cpuinfo % 8)) == 7
    py.test.raises(ValueError,
            'detect_arch_version(write_cpuinfo(cpuinfo % 5))')
    assert detect_arch_version(write_cpuinfo(cpuinfo2)) == 6
