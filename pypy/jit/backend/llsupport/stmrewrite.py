from pypy.jit.backend.llsupport.rewrite import GcRewriterAssembler
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.metainterp.history import BoxPtr, ConstPtr, ConstInt

#
# STM Support
# -----------    
#
# Any SETFIELD_GC, SETARRAYITEM_GC, SETINTERIORFIELD_GC must be done on a
# W object.  The operation that forces an object p1 to be W is
# COND_CALL_GC_WB(p1, 0, descr=x2Wdescr), for x in 'PGORL'.  This
# COND_CALL_GC_WB is a bit special because if p1 is not W, it *replaces*
# its value with the W copy (by changing the register's value and
# patching the stack location if any).  It's still conceptually the same
# object, but the pointer is different.
#
# The case of GETFIELD_GC & friends is similar, excepted that it goes to
# a R or L object (at first, always a R object).
#
# The name "x2y" of write barriers is called the *category* or "cat".
#


class GcStmRewriterAssembler(GcRewriterAssembler):
    # This class performs the same rewrites as its base class,
    # plus the rewrites described in stm.txt.

    def __init__(self, *args):
        GcRewriterAssembler.__init__(self, *args)
        self.known_local = set()    # set of variables
        self.always_inevitable = False

    def rewrite(self, operations):
        # overridden method from parent class
        #
        for op in operations:
            if op.getopnum() == rop.DEBUG_MERGE_POINT:
                continue
            # ----------  pure operations, guards  ----------
            if op.is_always_pure() or op.is_guard() or op.is_ovf():
                self.newops.append(op)
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
                                 rop.SETINTERIORFIELD_GC,
                                 rop.STRSETITEM,
                                 rop.UNICODESETITEM):
                self.handle_setfield_operations(op)
                continue
            # ----------  mallocs  ----------
            if op.is_malloc():
                self.handle_malloc_operation(op)
                continue
            # ----------  calls  ----------
            if op.is_call():
                self.known_local.clear()
                if op.getopnum() == rop.CALL_RELEASE_GIL:
                    self.fallback_inevitable(op)
                else:
                    self.newops.append(op)
                continue
            # ----------  copystrcontent  ----------
            if op.getopnum() in (rop.COPYSTRCONTENT,
                                 rop.COPYUNICODECONTENT):
                self.handle_copystrcontent(op)
                continue
            # ----------  labels  ----------
            if op.getopnum() == rop.LABEL:
                self.known_local.clear()
                self.always_inevitable = False
                self.newops.append(op)
                continue
            # ----------  jump, finish, other ignored ops  ----------
            if op.getopnum() in (rop.JUMP,
                                 rop.FINISH,
                                 rop.FORCE_TOKEN,
                                 rop.READ_TIMESTAMP,
                                 rop.MARK_OPAQUE_PTR,
                                 rop.JIT_DEBUG,
                                 rop.KEEPALIVE,
                                 ):
                self.newops.append(op)
                continue
            # ----------  fall-back  ----------
            self.fallback_inevitable(op)
            #
        return self.newops


    def gen_write_barrier(self, v_base, cat):
        v_base = self.unconstifyptr(v_base)
        assert isinstance(v_base, BoxPtr)
        if v_base in self.known_local:
            return v_base    # no write barrier needed
        write_barrier_descr = getattr(self.gc_ll_descr, '%sdescr' % (cat,))
        args = [v_base, self.c_zero]
        self.newops.append(ResOperation(rop.COND_CALL_GC_WB, args, None,
                                        descr=write_barrier_descr))
        self.known_local.add(v_base)
        return v_base

    def unconstifyptr(self, v):
        if isinstance(v, ConstPtr):
            v_in = v
            v_out = BoxPtr()
            self.newops.append(ResOperation(rop.SAME_AS, [v_in], v_out))
            v = v_out
        assert isinstance(v, BoxPtr)
        return v

    def handle_setfield_operations(self, op):
        lst = op.getarglist()
        lst[0] = self.gen_write_barrier(lst[0], 'P2W')
        self.newops.append(op.copy_and_change(op.getopnum(), args=lst))

    def handle_malloc_operation(self, op):
        GcRewriterAssembler.handle_malloc_operation(self, op)
        self.known_local.add(op.result)

    def handle_getfield_operations(self, op):
        lst = op.getarglist()
        if lst[0] in self.known_local:
            self.newops.append(op)
            return
        lst[0] = self.unconstifyptr(lst[0])
        write_barrier_descr = self.gc_ll_descr.write_barrier_descr
        op_before = ResOperation(rop.STM_READ_BEFORE, [lst[0]], None,
                                 descr=write_barrier_descr)
        op_after  = ResOperation(rop.STM_READ_AFTER, [lst[0]], None)
        self.newops.append(op_before)
        self.newops.append(op.copy_and_change(op.getopnum(), args=lst))
        self.newops.append(op_after)

    def handle_copystrcontent(self, op):
        # first, a write barrier on the target string
        lst = op.getarglist()
        lst[1] = self.gen_write_barrier(lst[1])
        op = op.copy_and_change(op.getopnum(), args=lst)
        # then a normal STM_READ_BEFORE/AFTER pair on the source string
        self.handle_getfield_operations(op)

    def fallback_inevitable(self, op):
        self.known_local.clear()
        if not self.always_inevitable:
            addr = self.gc_ll_descr.get_malloc_fn_addr('stm_try_inevitable')
            descr = self.gc_ll_descr.stm_try_inevitable_descr
            op1 = ResOperation(rop.CALL, [ConstInt(addr)], None, descr=descr)
            self.newops.append(op1)
            self.always_inevitable = True
        self.newops.append(op)
