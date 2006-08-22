from pypy.jit.codegen.i386.ri386 import *
from pypy.jit.codegen.i386.codebuf import MachineCodeBlock


def test_machinecodeblock():
    mc = MachineCodeBlock(4096)
    mc.MOV(eax, mem(esp, 4))
    mc.SUB(eax, mem(esp, 8))
    mc.RET()

    res = mc.execute(44, 2)
    assert res == 42
    return res

def test_compile():
    from pypy.translator.c.test.test_genc import compile

    fn = compile(test_machinecodeblock, [])
    res = fn()
    assert res == 42
