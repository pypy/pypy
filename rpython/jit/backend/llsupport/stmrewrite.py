from rpython.jit.backend.llsupport.rewrite import GcRewriterAssembler
from rpython.jit.backend.llsupport.descr import (
    CallDescr, FieldDescr, InteriorFieldDescr, ArrayDescr)
from rpython.jit.metainterp.resoperation import ResOperation, rop
from rpython.jit.metainterp.history import BoxPtr, ConstPtr, ConstInt
from rpython.rlib.objectmodel import specialize
from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib.debug import (have_debug_prints, debug_start, debug_stop,
                                debug_print)
from rpython.jit.codewriter.effectinfo import EffectInfo


class GcStmRewriterAssembler(GcRewriterAssembler):
    # This class performs the same rewrites as its base class,
    # plus the rewrites described above.

    def __init__(self, *args):
        GcRewriterAssembler.__init__(self, *args)
        self.always_inevitable = False

    def other_operation(self, op):
        opnum = op.getopnum()
        if opnum == rop.INCREMENT_DEBUG_COUNTER:
            self.newops.append(op)
            return
        # ----------  transaction breaks  ----------
        if opnum == rop.STM_TRANSACTION_BREAK:
            # XXX redo!
            #self.emitting_an_operation_that_can_collect()
            #self.next_op_may_be_in_new_transaction()
            #self.newops.append(op)
            return
        # ----------  pure operations, guards  ----------
        if op.is_always_pure() or op.is_guard() or op.is_ovf():
            self.newops.append(op)
            return
        # ----------  non-pure getfields  ----------
        if opnum in (rop.GETFIELD_GC, rop.GETARRAYITEM_GC,
                     rop.GETINTERIORFIELD_GC):
            self.handle_getfields(op)
            return
        # ----------  calls  ----------
        if op.is_call():
            if opnum == rop.CALL_RELEASE_GIL:
                # self.fallback_inevitable(op)
                # is done by assembler._release_gil_shadowstack()
                self.newops.append(op)
            elif opnum == rop.CALL_ASSEMBLER:
                assert 0   # case handled by the parent class
            else:
                # only insert become_inevitable if calling a
                # non-transactionsafe and non-releasegil function
                descr = op.getdescr()
                assert not descr or isinstance(descr, CallDescr)

                if not descr or not descr.get_extra_info() \
                      or descr.get_extra_info().call_needs_inevitable():
                    self.fallback_inevitable(op)
                else:
                    self.newops.append(op)
            return
        # ----------  copystrcontent  ----------
        if opnum in (rop.COPYSTRCONTENT, rop.COPYUNICODECONTENT):
            self.handle_copystrcontent(op)
            continue
        XXX
        # ----------  raw getfields and setfields  ----------
        if opnum in (rop.GETFIELD_RAW, rop.SETFIELD_RAW):
            if self.maybe_handle_raw_accesses(op):
                continue
        # ----------  labels  ----------
        if opnum == rop.LABEL:
            self.emitting_an_operation_that_can_collect()
            self.next_op_may_be_in_new_transaction()
            
            self.newops.append(op)
            continue
        # ----------  jumps  ----------
        if opnum == rop.JUMP:
            self.newops.append(op)
            continue
        # ----------  finish, other ignored ops  ----------
        if opnum in (rop.FINISH, rop.FORCE_TOKEN,
                    rop.READ_TIMESTAMP, rop.MARK_OPAQUE_PTR,
                    rop.JIT_DEBUG, rop.KEEPALIVE,
                    rop.QUASIIMMUT_FIELD, rop.RECORD_KNOWN_CLASS,
                    ):
            self.newops.append(op)
            continue
        # ----------  fall-back  ----------
        # Check that none of the ops handled here can_collect
        # or cause a transaction break. This is not done by
        # the fallback here
        self.fallback_inevitable(op)
        debug_print("fallback for", op.repr())

    def emitting_an_operation_that_can_collect(self):
        GcRewriterAssembler.emitting_an_operation_that_can_collect(self)
        self.invalidate_write_categories()
    
    def next_op_may_be_in_new_transaction(self):
        self.known_lengths.clear() # XXX: check if really necessary or
                                   # just for labels
        self.known_category.clear()
        self.always_inevitable = False

    def invalidate_write_categories(self):
        for v, c in self.known_category.items():
            if c == 'W':
                self.known_category[v] = 'V'

    def invalidate_read_categories(self, reason):
        # XXX: needs aliasing info to be better
        # XXX: move to optimizeopt to only invalidate same typed vars?
        for v, c in self.known_category.items():
            if c == 'R':
                self.known_category[v] = 'Q'

    
    def get_barrier_descr(self, from_cat, to_cat):
        # compare with translator.stm.funcgen.stm_barrier
        # XXX: specialize more with info of IMMUTABLE and NOPTR
        if from_cat >= to_cat:
            return None
        
        gc = self.gc_ll_descr
        if to_cat == 'W':
            if from_cat >= 'V':
                return gc.V2Wdescr
            return gc.A2Wdescr
        elif to_cat == 'V':
            return gc.A2Vdescr
        elif to_cat == 'R':
            if from_cat >= 'Q':
                return gc.Q2Rdescr
            return gc.A2Rdescr
        elif to_cat == 'I':
            return gc.A2Idescr

    def gen_initialize_tid(self, v_newgcobj, tid):
        GcRewriterAssembler.gen_initialize_tid(self, v_newgcobj, tid)
        if self.gc_ll_descr.fielddescr_rev is not None:
            op = ResOperation(rop.STM_SET_REVISION_GC, [v_newgcobj,], None,
                              descr=self.gc_ll_descr.fielddescr_rev)
            self.newops.append(op)
            
    def gen_write_barrier(self, v):
        raise NotImplementedError

    def gen_barrier(self, v_base, target_category):
        v_base = self.unconstifyptr(v_base)
        assert isinstance(v_base, BoxPtr)
        source_category = self.known_category.get(v_base, 'A')
        write_barrier_descr = self.get_barrier_descr(source_category,
                                                     target_category)
        if write_barrier_descr is None:
            return v_base    # no barrier needed

        if target_category in ('W', 'V'):
            # if *any* of the readable vars is the same object,
            # it must repeat the read_barrier now
            self.invalidate_read_categories(v_base)

        args = [v_base,]
        op = rop.COND_CALL_STM_B
        self.newops.append(ResOperation(op, args, None,
                                        descr=write_barrier_descr))
        
        self.known_category[v_base] = target_category
        return v_base

    def unconstifyptr(self, v):
        if isinstance(v, ConstPtr):
            v_in = v
            v_out = BoxPtr()
            self.newops.append(ResOperation(rop.SAME_AS, [v_in], v_out))
            v = v_out
        assert isinstance(v, BoxPtr)
        return v

    def handle_getfields(self, op):
        opnum = op.getopnum()
        descr = op.getdescr()
        target_category = 'R'
        # XXX: review:
        # if opnum == rop.GETFIELD_GC:
        #     assert isinstance(descr, FieldDescr)
        #     if descr.is_immutable():
        #         target_category = 'I'
        # elif opnum == rop.GETINTERIORFIELD_GC:
        #     assert isinstance(descr, InteriorFieldDescr)
        #     if descr.is_immutable():
        #         target_category = 'I'
        # elif opnum == rop.GETARRAYITEM_GC:
        #     assert isinstance(descr, ArrayDescr)
        #     if descr.is_immutable():
        #         target_category = 'I'
                
        self.handle_category_operations(op, target_category)

    
    def handle_setfields(self, op):
        opnum = op.getopnum()
        descr = op.getdescr()
        target_category = 'W'
        if opnum == rop.SETFIELD_GC:
            assert isinstance(descr, FieldDescr)
            if not descr.is_pointer_field():
                target_category = 'V'
        elif opnum == rop.SETINTERIORFIELD_GC:
            assert isinstance(descr, InteriorFieldDescr)
            if not descr.is_pointer_field():
                target_category = 'V'
        elif opnum == rop.SETARRAYITEM_GC:
            assert isinstance(descr, ArrayDescr)
            if not descr.is_array_of_pointers():
                target_category = 'V'
        elif opnum in (rop.STRSETITEM, rop.UNICODESETITEM):
            target_category = 'V'
            
        self.handle_category_operations(op, target_category)

    
    def handle_category_operations(self, op, target_category):
        lst = op.getarglist()
        lst[0] = self.gen_barrier(lst[0], target_category)
        self.newops.append(op.copy_and_change(op.getopnum(), args=lst))

    def handle_malloc_operation(self, op):
        GcRewriterAssembler.handle_malloc_operation(self, op)
        self.known_category[op.result] = 'W'

    def handle_copystrcontent(self, op):
        # first, a write barrier on the target string
        lst = op.getarglist()
        lst[1] = self.gen_barrier(lst[1], 'W')
        op = op.copy_and_change(op.getopnum(), args=lst)
        # then an immutable read barrier the source string
        # XXX: 'I' enough?
        self.handle_category_operations(op, 'R')

    @specialize.arg(1)
    def _do_stm_call(self, funcname, args, result):
        addr = self.gc_ll_descr.get_malloc_fn_addr(funcname)
        descr = getattr(self.gc_ll_descr, funcname + '_descr')
        op1 = ResOperation(rop.CALL, [ConstInt(addr)] + args,
                           result, descr=descr)
        self.newops.append(op1)

    def fallback_inevitable(self, op):
        self.known_category.clear()
        if not self.always_inevitable:
            self.emitting_an_operation_that_can_collect()
            self._do_stm_call('stm_try_inevitable', [], None)
            self.always_inevitable = True
        self.newops.append(op)

    def _is_null(self, box):
        return isinstance(box, ConstPtr) and not box.value

    def maybe_handle_raw_accesses(self, op):
        from rpython.jit.backend.llsupport.descr import FieldDescr
        descr = op.getdescr()
        assert isinstance(descr, FieldDescr)
        if descr.stm_dont_track_raw_accesses:
            self.newops.append(op)
            return True
        return False
