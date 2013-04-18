import py
from rpython.tool.udir import udir
from rpython.jit.backend.arm.detect import detect_arch_version

cpuinfo = "Processor : ARMv%d-compatible processor rev 7 (v6l)"""


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
    py.test.raises(ValueError,
            'detect_arch_version(write_cpuinfo("Lorem ipsum dolor sit amet, consectetur"))')
