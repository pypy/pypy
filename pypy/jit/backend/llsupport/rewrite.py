import sys
from pypy.rlib.rarithmetic import ovfcheck
from pypy.jit.metainterp.history import ConstInt, BoxPtr, ConstPtr, BoxInt
from pypy.jit.metainterp.resoperation import ResOperation, rop
from pypy.jit.codewriter import heaptracker
from pypy.jit.backend.llsupport.symbolic import WORD
from pypy.jit.backend.llsupport.descr import SizeDescr, ArrayDescr


class GcRewriterAssembler(object):
    # This class performs the following rewrites on the list of operations:
    #
    # - Remove the DEBUG_MERGE_POINTs.
    #
    # - Turn all NEW_xxx to either a CALL_MALLOC_GC, or a CALL_MALLOC_NURSERY
    #   followed by SETFIELDs in order to initialize their GC fields.  The
    #   two advantages of CALL_MALLOC_NURSERY is that it inlines the common
    #   path, and we need only one such operation to allocate several blocks
    #   of memory at once.
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
        self.newops = []
        self.known_lengths = {}
        self.recent_mallocs = {}     # set of variables

    def rewrite(self, operations):
        # we can only remember one malloc since the next malloc can possibly
        # collect; but we can try to collapse several known-size mallocs into
        # one, both for performance and to reduce the number of write
        # barriers.  We do this on each "basic block" of operations, which in
        # this case means between CALLs or unknown-size mallocs.
        #
        for op in operations:
            if op.getopnum() == rop.DEBUG_MERGE_POINT:
                continue
            # ---------- turn NEWxxx into CALL_MALLOC_xxx ----------
            if op.is_malloc():
                self.handle_malloc_operation(op)
                continue
            elif op.can_malloc():
                self.emitting_an_operation_that_can_collect()
            elif op.getopnum() == rop.LABEL:
                self.emitting_an_operation_that_can_collect()
                self.known_lengths.clear()
            # ---------- write barriers ----------
            if self.gc_ll_descr.write_barrier_descr is not None:
                if op.getopnum() == rop.SETFIELD_GC:
                    self.handle_write_barrier_setfield(op)
                    continue
                if op.getopnum() == rop.SETINTERIORFIELD_GC:
                    self.handle_write_barrier_setinteriorfield(op)
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
            assert isinstance(descr, ArrayDescr)
            self.handle_new_array(descr, op)
        elif opnum == rop.NEWSTR:
            self.handle_new_array(self.gc_ll_descr.str_descr, op)
        elif opnum == rop.NEWUNICODE:
            self.handle_new_array(self.gc_ll_descr.unicode_descr, op)
        else:
            raise NotImplementedError(op.getopname())

    def handle_new_fixedsize(self, descr, op):
        assert isinstance(descr, SizeDescr)
        size = descr.size
        in_nursery = self.gen_malloc_nursery(size, op.result)
        self.gen_initialize_tid(op.result, descr.tid, in_nursery)

    def handle_new_array(self, arraydescr, op):
        v_length = op.getarg(0)
        total_size = -1
        if isinstance(v_length, ConstInt):
            num_elem = v_length.getint()
            self.known_lengths[op.result] = num_elem
            try:
                var_size = ovfcheck(arraydescr.itemsize * num_elem)
                total_size = ovfcheck(arraydescr.basesize + var_size)
            except OverflowError:
                pass    # total_size is still -1
        elif arraydescr.itemsize == 0:
            total_size = arraydescr.basesize
        if 0 <= total_size <= 0xffffff:     # up to 16MB, arbitrarily
            in_nursery = self.gen_malloc_nursery(total_size, op.result)
            self.gen_initialize_tid(op.result, arraydescr.tid, in_nursery)
            self.gen_initialize_len(op.result, v_length, arraydescr.lendescr)
        elif self.gc_ll_descr.kind == 'boehm':
            self.gen_boehm_malloc_array(arraydescr, v_length, op.result)
        else:
            opnum = op.getopnum()
            if opnum == rop.NEW_ARRAY:
                self.gen_malloc_array(arraydescr, v_length, op.result)
            elif opnum == rop.NEWSTR:
                self.gen_malloc_str(v_length, op.result)
            elif opnum == rop.NEWUNICODE:
                self.gen_malloc_unicode(v_length, op.result)
            else:
                raise NotImplementedError(op.getopname())

    # ----------

    def emitting_an_operation_that_can_collect(self):
        # must be called whenever we emit an operation that can collect:
        # forgets the previous MALLOC_NURSERY, if any; and empty the
        # set 'recent_mallocs', so that future SETFIELDs will generate
        # a write barrier as usual.
        self._op_malloc_nursery = None
        self.recent_mallocs.clear()

    def _gen_call_malloc_gc(self, args, v_result, descr):
        """Generate a CALL_MALLOC_GC with the given args."""
        self.emitting_an_operation_that_can_collect()
        op = ResOperation(rop.CALL_MALLOC_GC, args, v_result, descr)
        self.newops.append(op)
        # mark 'v_result' as freshly malloced
        self.recent_mallocs[v_result] = None

    def gen_malloc_fixedsize(self, size, v_result):
        """Generate a CALL_MALLOC_GC(malloc_fixedsize_fn, Const(size)).
        Note that with the framework GC, this should be called very rarely.
        """
        addr = self.gc_ll_descr.get_malloc_fn_addr('malloc_fixedsize')
        self._gen_call_malloc_gc([ConstInt(addr), ConstInt(size)], v_result,
                                 self.gc_ll_descr.malloc_fixedsize_descr)

    def gen_boehm_malloc_array(self, arraydescr, v_num_elem, v_result):
        """Generate a CALL_MALLOC_GC(malloc_array_fn, ...) for Boehm."""
        addr = self.gc_ll_descr.get_malloc_fn_addr('malloc_array')
        self._gen_call_malloc_gc([ConstInt(addr),
                                  ConstInt(arraydescr.basesize),
                                  v_num_elem,
                                  ConstInt(arraydescr.itemsize),
                                  ConstInt(arraydescr.lendescr.offset)],
                                 v_result,
                                 self.gc_ll_descr.malloc_array_descr)

    def gen_malloc_array(self, arraydescr, v_num_elem, v_result):
        """Generate a CALL_MALLOC_GC(malloc_array_fn, ...) going either
        to the standard or the nonstandard version of the function."""
        #
        if (arraydescr.basesize == self.gc_ll_descr.standard_array_basesize
            and arraydescr.lendescr.offset ==
                self.gc_ll_descr.standard_array_length_ofs):
            # this is a standard-looking array, common case
            addr = self.gc_ll_descr.get_malloc_fn_addr('malloc_array')
            args = [ConstInt(addr),
                    ConstInt(arraydescr.itemsize),
                    ConstInt(arraydescr.tid),
                    v_num_elem]
            calldescr = self.gc_ll_descr.malloc_array_descr
        else:
            # rare case, so don't care too much about the number of arguments
            addr = self.gc_ll_descr.get_malloc_fn_addr(
                                              'malloc_array_nonstandard')
            args = [ConstInt(addr),
                    ConstInt(arraydescr.basesize),
                    ConstInt(arraydescr.itemsize),
                    ConstInt(arraydescr.lendescr.offset),
                    ConstInt(arraydescr.tid),
                    v_num_elem]
            calldescr = self.gc_ll_descr.malloc_array_nonstandard_descr
        self._gen_call_malloc_gc(args, v_result, calldescr)

    def gen_malloc_str(self, v_num_elem, v_result):
        """Generate a CALL_MALLOC_GC(malloc_str_fn, ...)."""
        addr = self.gc_ll_descr.get_malloc_fn_addr('malloc_str')
        self._gen_call_malloc_gc([ConstInt(addr), v_num_elem], v_result,
                                 self.gc_ll_descr.malloc_str_descr)

    def gen_malloc_unicode(self, v_num_elem, v_result):
        """Generate a CALL_MALLOC_GC(malloc_unicode_fn, ...)."""
        addr = self.gc_ll_descr.get_malloc_fn_addr('malloc_unicode')
        self._gen_call_malloc_gc([ConstInt(addr), v_num_elem], v_result,
                                 self.gc_ll_descr.malloc_unicode_descr)

    def gen_malloc_nursery(self, size, v_result):
        """Try to generate or update a CALL_MALLOC_NURSERY.
        If that fails, generate a plain CALL_MALLOC_GC instead.
        """
        size = self.round_up_for_allocation(size)
        if not self.gc_ll_descr.can_use_nursery_malloc(size):
            self.gen_malloc_fixedsize(size, v_result)
            return False
        #
        op = None
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
            op = ResOperation(rop.CALL_MALLOC_NURSERY,
                              [ConstInt(size)],
                              v_result)
            self._op_malloc_nursery = op
        #
        self.newops.append(op)
        self._previous_size = size
        self._v_last_malloced_nursery = v_result
        self.recent_mallocs[v_result] = None
        return True

    def gen_initialize_tid(self, v_newgcobj, tid, in_nursery):
        if self.gc_ll_descr.fielddescr_tid is not None:
            # produce a SETFIELD to initialize the GC header
            v_tid = ConstInt(tid)
            if not in_nursery:
                # important: must preserve the gcflags!  rare case.
                v_tidbase = BoxInt()
                v_tidcombined = BoxInt()
                op = ResOperation(rop.GETFIELD_RAW,
                                  [v_newgcobj], v_tidbase,
                                  descr=self.gc_ll_descr.fielddescr_tid)
                self.newops.append(op)
                op = ResOperation(rop.INT_OR,
                                  [v_tidbase, v_tid], v_tidcombined)
                self.newops.append(op)
                v_tid = v_tidcombined
            op = ResOperation(rop.SETFIELD_GC,
                              [v_newgcobj, v_tid], None,
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

    def handle_write_barrier_setinteriorfield(self, op):
        val = op.getarg(0)
        # no need for a write barrier in the case of previous malloc
        if val not in self.recent_mallocs:
            v = op.getarg(2)
            if isinstance(v, BoxPtr) or (isinstance(v, ConstPtr) and
                                         bool(v.value)): # store a non-NULL
                self.gen_write_barrier(op.getarg(0), v)
                op = op.copy_and_change(rop.SETINTERIORFIELD_RAW)
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
        if write_barrier_descr.has_write_barrier_from_array(self.cpu):
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
        if not self.gc_ll_descr.round_up:
            return size
        if self.gc_ll_descr.translate_support_code:
            from pypy.rpython.lltypesystem import llarena
            return llarena.round_up_for_allocation(
                size, self.gc_ll_descr.minimal_size_in_nursery)
        else:
            # non-translated: do it manually
            # assume that "self.gc_ll_descr.minimal_size_in_nursery" is 2 WORDs
            size = max(size, 2 * WORD)
            return (size + WORD-1) & ~(WORD-1)     # round up
