from pypy.jit.codegen.i386.ri386 import *
from pypy.jit.codegen.i386.codebuf import MachineCodeBlock, memhandler


def test_alloc_free():
    map_size = 65536
    data = memhandler.alloc(map_size)
    for i in range(0, map_size, 171):
        data[i] = chr(i & 0xff)
    for i in range(0, map_size, 171):
        assert data[i] == chr(i & 0xff)
    memhandler.free(data, map_size)

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
