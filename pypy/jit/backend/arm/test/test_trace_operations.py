from pypy.jit.backend.x86.test.test_regalloc import BaseTestRegalloc
from pypy.jit.backend.detect_cpu import getcpuclass
from pypy.rpython.lltypesystem import lltype, llmemory
CPU = getcpuclass()

class TestConstPtr(BaseTestRegalloc):

    cpu = CPU(None, None)
    #cpu.gc_ll_descr = MockGcDescr(False)
    cpu.setup_once()

    S = lltype.GcForwardReference()
    S.become(lltype.GcStruct('S', ('field', lltype.Ptr(S)),
                             ('int', lltype.Signed)))

    fielddescr = cpu.fielddescrof(S, 'field')

    struct_ptr = lltype.malloc(S)
    struct_ref = lltype.cast_opaque_ptr(llmemory.GCREF, struct_ptr)
    #child_ptr = lltype.nullptr(S)
    #struct_ptr.field = child_ptr


    #descr0 = cpu.fielddescrof(S, 'int')
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

