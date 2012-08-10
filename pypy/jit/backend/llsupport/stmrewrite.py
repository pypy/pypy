from pypy.jit.backend.llsupport.rewrite import GcRewriterAssembler
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.history import BoxPtr, ConstPtr


class GcStmRewriterAssembler(GcRewriterAssembler):
    # This class performs the same rewrites as its base class,
    # plus the rewrites described in stm.txt.

    def __init__(self, *args):
        GcRewriterAssembler.__init__(self, *args)
        self.known_local = set()    # set of variables

    def rewrite(self, operations):
        # overridden method from parent class
        #
        for op in operations:
            if op.getopnum() == rop.DEBUG_MERGE_POINT:
                continue
            # ----------  getfields  ----------
            if op.getopnum() in (rop.GETFIELD_GC,
                                 rop.GETARRAYITEM_GC,
                                 rop.GETINTERIORFIELD_GC):
                self.handle_getfield_operations(op)
                continue
            # ----------  setfields  ----------
            if op.getopnum() in (rop.SETFIELD_GC,
                                 rop.SETARRAYITEM_GC,
                                 rop.SETINTERIORFIELD_GC):
                self.handle_setfield_operations(op)
                continue
            # ----------  mallocs  ----------
            if op.is_malloc():
                self.handle_malloc_operation(op)
                continue
            # ----------  calls, labels  ----------
            if op.is_call() or op.getopnum() == rop.LABEL:
                self.known_local.clear()
            # ----------
            self.newops.append(op)
        return self.newops


    def gen_write_barrier(self, v_base):
        assert isinstance(v_base, BoxPtr)
        if v_base in self.known_local:
            return    # no write barrier needed
        write_barrier_descr = self.gc_ll_descr.write_barrier_descr
        args = [v_base, self.c_zero]
        self.newops.append(ResOperation(rop.COND_CALL_GC_WB, args, None,
                                        descr=write_barrier_descr))
        self.known_local.add(v_base)

    def unconstifyptr(self, v):
        if isinstance(v, ConstPtr):
            v_in = v
            v_out = BoxPtr()
            self.newops.append(ResOperation(rop.SAME_AS, [v_in], v_out))
            v = v_out
        assert isinstance(v, BoxPtr)
        return v

    def handle_setfield_operations(self, op):
        self.gen_write_barrier(self.unconstifyptr(op.getarg(0)))
        self.newops.append(op)

    def handle_malloc_operation(self, op):
        GcRewriterAssembler.handle_malloc_operation(self, op)
        self.known_local.add(op.result)

    def handle_getfield_operations(self, op):
        lst = op.getarglist()
        lst[0] = self.unconstifyptr(lst[0])
        self.newops.append(OP_STM_READ_BEFORE)
        self.newops.append(op.copy_and_change(op.getopnum(), args=lst))
        self.newops.append(OP_STM_READ_AFTER)


OP_STM_READ_BEFORE = ResOperation(rop.STM_READ_BEFORE, [], None)
OP_STM_READ_AFTER  = ResOperation(rop.STM_READ_AFTER, [], None)
