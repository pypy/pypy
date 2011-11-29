from pypy.rlib.rarithmetic import ovfcheck
from pypy.jit.metainterp.history import ConstInt
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.codewriter import heaptracker
from pypy.jit.backend.llsupport.symbolic import WORD
from pypy.jit.backend.llsupport.descr import BaseSizeDescr, BaseArrayDescr


class GcRewriterAssembler(object):
    # This class performs the following rewrites on the list of operations:
    #
    # - Remove the DEBUG_MERGE_POINTs.
    #
    # - Turn all NEW_xxx to MALLOC_GC operations, possibly followed by
    #   SETFIELDs in order to initialize their GC fields.
    #
    # - Add COND_CALLs to the write barrier before SETFIELD_GC and
    #   SETARRAYITEM_GC operations.

    _previous_size = -1
    _op_malloc_nursery = None
    _v_last_malloced_nursery = None
    c_zero = ConstInt(0)

    def __init__(self, gc_ll_descr, cpu):
        self.gc_ll_descr = gc_ll_descr
        self.cpu = cpu
        self.tsc = self.gc_ll_descr.translate_support_code
        self.newops = []
        self.known_lengths = {}
        self.recent_mallocs = {}     # set of variables

    def rewrite(self, operations):
        # we can only remember one malloc since the next malloc can possibly
        # collect; but we can try to collapse several known-size mallocs into
        # one, both for performance and to reduce the number of write
        # barriers.  We do this on each "basic block" of operations, which in
        # this case means between CALLs or unknown-size mallocs.
        # (XXX later: or LABELs)
        #
        for op in operations:
            if op.getopnum() == rop.DEBUG_MERGE_POINT:
                continue
            # ---------- fold the NEWxxx operations into MALLOC_GC ----------
            if op.is_malloc():
                self.handle_malloc_operation(op)
                continue
            elif op.can_malloc():
                self.emitting_an_operation_that_can_collect()
            # ---------- write barriers ----------
            if self.gc_ll_descr.write_barrier_descr is not None:
                if op.getopnum() == rop.SETFIELD_GC:
                    self.handle_write_barrier_setfield(op)
                    continue
                if op.getopnum() == rop.SETARRAYITEM_GC:
                    self.handle_write_barrier_setarrayitem(op)
                    continue
            # ----------
            self.newops.append(op)
        return self.newops

    # ----------

    def handle_malloc_operation(self, op):
        opnum = op.getopnum()
        if opnum == rop.NEW:
            self.handle_new_fixedsize(op.getdescr(), op)
        elif opnum == rop.NEW_WITH_VTABLE:
            classint = op.getarg(0).getint()
            descr = heaptracker.vtable2descr(self.cpu, classint)
            self.handle_new_fixedsize(descr, op)
            if self.gc_ll_descr.fielddescr_vtable is not None:
                op = ResOperation(rop.SETFIELD_GC,
                                  [op.result, ConstInt(classint)], None,
                                  descr=self.gc_ll_descr.fielddescr_vtable)
                self.newops.append(op)
        elif opnum == rop.NEW_ARRAY:
            descr = op.getdescr()
            assert isinstance(descr, BaseArrayDescr)
            self.handle_new_array(descr.tid,
                                  descr.get_base_size(self.tsc),
                                  descr.get_item_size(self.tsc),
                                  descr.field_arraylen_descr,
                                  op)
        elif opnum == rop.NEWSTR:
            self.handle_new_array(self.gc_ll_descr.str_type_id,
                                  self.gc_ll_descr.str_basesize,
                                  self.gc_ll_descr.str_itemsize,
                                  self.gc_ll_descr.field_strlen_descr,
                                  op)
        elif opnum == rop.NEWUNICODE:
            self.handle_new_array(self.gc_ll_descr.unicode_type_id,
                                  self.gc_ll_descr.unicode_basesize,
                                  self.gc_ll_descr.unicode_itemsize,
                                  self.gc_ll_descr.field_unicodelen_descr,
                                  op)
        else:
            raise NotImplementedError(op.getopname())

    def handle_new_fixedsize(self, descr, op):
        assert isinstance(descr, BaseSizeDescr)
        size = descr.size
        self.gen_malloc_nursery(size, op.result)
        self.gen_initialize_tid(op.result, descr.tid)

    def handle_new_array(self, tid, base_size, item_size, arraylen_descr, op):
        v_length = op.getarg(0)
        total_size = -1
        if item_size == 0:
            total_size = base_size
        elif isinstance(v_length, ConstInt):
            num_elem = v_length.getint()
            try:
                var_size = ovfcheck(item_size * num_elem)
                total_size = ovfcheck(base_size + var_size)
            except OverflowError:
                pass
        if total_size >= 0:
            self.gen_malloc_nursery(total_size, op.result)
        else:
            self.gen_malloc_gc(base_size, op.result,
                               v_length, ConstInt(item_size))
        self.gen_initialize_tid(op.result, tid)
        self.gen_initialize_len(op.result, v_length, arraylen_descr)

    # ----------

    def emitting_an_operation_that_can_collect(self):
        # must be called whenever we emit an operation that can collect:
        # forgets the previous MALLOC_NURSERY, if any; and empty the
        # set 'recent_mallocs', so that future SETFIELDs will generate
        # a write barrier as usual.
        self._op_malloc_nursery = None
        self.recent_mallocs.clear()

    def gen_malloc_gc(self, size, v_result,
                      v_num_elem=c_zero, c_item_size=c_zero):
        """Generate a MALLOC_GC."""
        c_size = ConstInt(size)
        self.emitting_an_operation_that_can_collect()
        op = ResOperation(rop.MALLOC_GC, [c_size, v_num_elem, c_item_size],
                          v_result)
        self.newops.append(op)
        # mark 'v_result' as freshly malloced
        self.recent_mallocs[v_result] = None

    def gen_malloc_nursery(self, size, v_result):
        """Try to generate or update a MALLOC_NURSERY.
        If that fails, generate a plain MALLOC_GC instead.
        """
        if not self.gc_ll_descr.can_use_nursery_malloc(size):
            self.gen_malloc_gc(size, v_result)
            return
        #
        size = self.round_up_for_allocation(size)
        op = None
        #
        if self._op_malloc_nursery is not None:
            # already a MALLOC_NURSERY: increment its total size
            total_size = self._op_malloc_nursery.getarg(0).getint()
            total_size += size
            if self.gc_ll_descr.can_use_nursery_malloc(total_size):
                # if the total size is still reasonable, merge it
                self._op_malloc_nursery.setarg(0, ConstInt(total_size))
                op = ResOperation(rop.INT_ADD,
                                  [self._v_last_malloced_nursery,
                                   ConstInt(self._previous_size)],
                                  v_result)
        if op is None:
            # if we failed to merge with a previous MALLOC_NURSERY, emit one
            self.emitting_an_operation_that_can_collect()
            op = ResOperation(rop.MALLOC_NURSERY, [ConstInt(size)], v_result)
            self._op_malloc_nursery = op
        #
        self.newops.append(op)
        self._previous_size = size
        self._v_last_malloced_nursery = v_result
        self.recent_mallocs[v_result] = None

    def gen_initialize_tid(self, v_newgcobj, tid):
        if self.gc_ll_descr.fielddescr_tid is not None:
            # produce a SETFIELD to initialize the GC header
            op = ResOperation(rop.SETFIELD_GC,
                              [v_newgcobj, ConstInt(tid)], None,
                              descr=self.gc_ll_descr.fielddescr_tid)
            self.newops.append(op)

    def gen_initialize_len(self, v_newgcobj, v_length, arraylen_descr):
        # produce a SETFIELD to initialize the array length
        op = ResOperation(rop.SETFIELD_GC,
                          [v_newgcobj, v_length], None,
                          descr=arraylen_descr)
        self.newops.append(op)

    # ----------

    def handle_write_barrier_setfield(self, op):
        val = op.getarg(0)
        # no need for a write barrier in the case of previous malloc
        if val not in self.recent_mallocs:
            v = op.getarg(1)
            if isinstance(v, BoxPtr) or (isinstance(v, ConstPtr) and
                                         bool(v.value)): # store a non-NULL
                self.gen_write_barrier(op.getarg(0), v)
                op = op.copy_and_change(rop.SETFIELD_RAW)
        self.newops.append(op)

    def handle_write_barrier_setarrayitem(self, op):
        val = op.getarg(0)
        # no need for a write barrier in the case of previous malloc
        if val not in self.recent_mallocs:
            v = op.getarg(2)
            if isinstance(v, BoxPtr) or (isinstance(v, ConstPtr) and
                                         bool(v.value)): # store a non-NULL
                self.gen_write_barrier_array(op.getarg(0),
                                             op.getarg(1), v)
                op = op.copy_and_change(rop.SETARRAYITEM_RAW)
        self.newops.append(op)

    def gen_write_barrier(self, v_base, v_value):
        write_barrier_descr = self.gc_ll_descr.write_barrier_descr
        args = [v_base, v_value]
        self.newops.append(ResOperation(rop.COND_CALL_GC_WB, args, None,
                                        descr=write_barrier_descr))

    def gen_write_barrier_array(self, v_base, v_index, v_value):
        write_barrier_descr = self.gc_ll_descr.write_barrier_descr
        if write_barrier_descr.get_write_barrier_from_array_fn(self.cpu) != 0:
            # If we know statically the length of 'v', and it is not too
            # big, then produce a regular write_barrier.  If it's unknown or
            # too big, produce instead a write_barrier_from_array.
            LARGE = 130
            length = self.known_lengths.get(v_base, LARGE)
            if length >= LARGE:
                # unknown or too big: produce a write_barrier_from_array
                args = [v_base, v_index, v_value]
                self.newops.append(
                    ResOperation(rop.COND_CALL_GC_WB_ARRAY, args, None,
                                 descr=write_barrier_descr))
                return
        # fall-back case: produce a write_barrier
        self.gen_write_barrier(v_base, v_value)

    def round_up_for_allocation(self, size):
        if self.tsc:
            return llarena.round_up_for_allocation(
                size, self.gc_ll_descr.minimal_size_in_nursery)
        else:
            # non-translated: do it manually
            # assume that "self.gc_ll_descr.minimal_size_in_nursery" is 2 WORDs
            size = max(size, 2 * WORD)
            return (size + WORD-1) & ~(WORD-1)     # round up
