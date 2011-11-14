from pypy.jit.backend.arm.test.support import skip_unless_arm
skip_unless_arm()

from pypy.jit.backend.x86.test.test_regalloc import BaseTestRegalloc
from pypy.jit.backend.detect_cpu import getcpuclass
from pypy.rpython.lltypesystem import lltype, llmemory
CPU = getcpuclass()

class TestConstPtr(BaseTestRegalloc):

    cpu = CPU(None, None)
    #cpu.gc_ll_descr = MockGcDescr(False)
    cpu.setup_once()

    S = lltype.GcForwardReference()
    fields = [('int%d' % i, lltype.Signed) for i in range(1050)]
    S.become(lltype.GcStruct('S', *fields))

    fielddescr = cpu.fielddescrof(S, 'int1049')

    struct_ptr = lltype.malloc(S)
    struct_ref = lltype.cast_opaque_ptr(llmemory.GCREF, struct_ptr)

    ptr0 = struct_ref

    namespace = locals().copy()

    def test_finish_failargs_constptr(self):
        ops = '''
        [i0]
        i1 = int_add(i0, 1)
        finish(i1, ConstPtr(ptr0))
        '''
        self.interpret(ops, [99])
        assert self.getint(0) == 100
        ptr = self.cpu.get_latest_value_ref(1)
        assert self.ptr0 == ptr

    def test_getfield_with_offset_gt_one_byte(self):
        self.struct_ptr.int1049 = 666
        ops = '''
        [p0]
        i0 = getfield_gc(p0, descr=fielddescr)
        finish(i0)
        '''
        self.interpret(ops, [self.struct_ptr])
        assert self.getint(0) == 666

    def test_setfield_with_offset_gt_one_byte(self):
        ops = '''
        [p0]
        setfield_gc(p0, 777, descr=fielddescr)
        finish()
        '''
        self.interpret(ops, [self.struct_ptr])
        assert self.struct_ptr.int1049 == 777
