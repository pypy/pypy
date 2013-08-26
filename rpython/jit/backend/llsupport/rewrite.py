from rpython.rlib.rarithmetic import ovfcheck
from rpython.rtyper.lltypesystem import llmemory
from rpython.jit.metainterp import history
from rpython.jit.metainterp.history import ConstInt, BoxPtr, ConstPtr
from rpython.jit.metainterp.resoperation import ResOperation, rop
from rpython.jit.codewriter import heaptracker
from rpython.jit.backend.llsupport.symbolic import WORD
from rpython.jit.backend.llsupport.descr import SizeDescr, ArrayDescr
from rpython.jit.metainterp.history import JitCellToken

FLAG_ARRAY = 0
FLAG_STR = 1
FLAG_UNICODE = 2

class GcRewriterAssembler(object):
    """ This class performs the following rewrites on the list of operations:

     - Remove the DEBUG_MERGE_POINTs.

     - Turn all NEW_xxx to either a CALL_MALLOC_GC, or a CALL_MALLOC_NURSERY
       followed by SETFIELDs in order to initialize their GC fields.  The
       two advantages of CALL_MALLOC_NURSERY is that it inlines the common
       path, and we need only one such operation to allocate several blocks
       of memory at once.

     - Add COND_CALLs to the write barrier before SETFIELD_GC and
       SETARRAYITEM_GC operations.

    'write_barrier_applied' contains a dictionary of variable -> None.
    If a variable is in the dictionary, next setfields can be called without
    a write barrier.  The idea is that an object that was freshly allocated
    or already write_barrier'd don't need another write_barrier if there
    was no potentially collecting resop inbetween.
    """

    _previous_size = -1
    _op_malloc_nursery = None
    _v_last_malloced_nursery = None
    c_zero = ConstInt(0)

    def __init__(self, gc_ll_descr, cpu):
        self.gc_ll_descr = gc_ll_descr
        self.cpu = cpu
        self.newops = []
        self.known_lengths = {}
        self.write_barrier_applied = {}

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
            # ---------- call assembler -----------
            if op.getopnum() == rop.CALL_ASSEMBLER:
                self.handle_call_assembler(op)
                continue
            #
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
            self.handle_new_array(self.gc_ll_descr.str_descr, op,
                                  kind=FLAG_STR)
        elif opnum == rop.NEWUNICODE:
            self.handle_new_array(self.gc_ll_descr.unicode_descr, op,
                                  kind=FLAG_UNICODE)
        else:
            raise NotImplementedError(op.getopname())

    def handle_new_fixedsize(self, descr, op):
        assert isinstance(descr, SizeDescr)
        size = descr.size
        if self.gen_malloc_nursery(size, op.result):
            self.gen_initialize_tid(op.result, descr.tid)
        else:
            self.gen_malloc_fixedsize(size, descr.tid, op.result)

    def handle_new_array(self, arraydescr, op, kind=FLAG_ARRAY):
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
        elif (self.gc_ll_descr.can_use_nursery_malloc(1) and
              self.gen_malloc_nursery_varsize(arraydescr.itemsize,
              v_length, op.result, arraydescr, kind=kind)):
            # note that we cannot initialize tid here, because the array
            # might end up being allocated by malloc_external or some
            # stuff that initializes GC header fields differently
            self.gen_initialize_len(op.result, v_length, arraydescr.lendescr)
            return
        if (total_size >= 0 and
                self.gen_malloc_nursery(total_size, op.result)):
            self.gen_initialize_tid(op.result, arraydescr.tid)
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

    def gen_malloc_frame(self, frame_info, frame, size_box):
        descrs = self.gc_ll_descr.getframedescrs(self.cpu)
        if self.gc_ll_descr.kind == 'boehm':
            op0 = ResOperation(rop.GETFIELD_GC, [history.ConstInt(frame_info)],
                               size_box,
                               descr=descrs.jfi_frame_depth)
            self.newops.append(op0)
            op1 = ResOperation(rop.NEW_ARRAY, [size_box], frame,
                               descr=descrs.arraydescr)
            self.handle_new_array(descrs.arraydescr, op1)
        else:
            # we read size in bytes here, not the length
            op0 = ResOperation(rop.GETFIELD_GC, [history.ConstInt(frame_info)],
                               size_box,
                               descr=descrs.jfi_frame_size)
            self.newops.append(op0)
            self.gen_malloc_nursery_varsize_frame(size_box, frame)
            self.gen_initialize_tid(frame, descrs.arraydescr.tid)
            length_box = history.BoxInt()
            op1 = ResOperation(rop.GETFIELD_GC, [history.ConstInt(frame_info)],
                               length_box,
                               descr=descrs.jfi_frame_depth)
            self.newops.append(op1)
            self.gen_initialize_len(frame, length_box,
                                    descrs.arraydescr.lendescr)

    def handle_call_assembler(self, op):
        descrs = self.gc_ll_descr.getframedescrs(self.cpu)
        loop_token = op.getdescr()
        assert isinstance(loop_token, history.JitCellToken)
        jfi = loop_token.compiled_loop_token.frame_info
        llfi = heaptracker.adr2int(llmemory.cast_ptr_to_adr(jfi))
        size_box = history.BoxInt()
        frame = history.BoxPtr()
        self.gen_malloc_frame(llfi, frame, size_box)
        op2 = ResOperation(rop.SETFIELD_GC, [frame, history.ConstInt(llfi)],
                           None, descr=descrs.jf_frame_info)
        self.newops.append(op2)
        arglist = op.getarglist()
        index_list = loop_token.compiled_loop_token._ll_initial_locs
        for i, arg in enumerate(arglist):
            descr = self.cpu.getarraydescr_for_frame(arg.type)
            assert self.cpu.JITFRAME_FIXED_SIZE & 1 == 0
            _, itemsize, _ = self.cpu.unpack_arraydescr_size(descr)
            index = index_list[i] // itemsize # index is in bytes
            self.newops.append(ResOperation(rop.SETARRAYITEM_GC,
                                            [frame, ConstInt(index),
                                             arg],
                                            None, descr))
        descr = op.getdescr()
        assert isinstance(descr, JitCellToken)
        jd = descr.outermost_jitdriver_sd
        args = [frame]
        if jd and jd.index_of_virtualizable >= 0:
            args = [frame, arglist[jd.index_of_virtualizable]]
        else:
            args = [frame]
        self.newops.append(ResOperation(rop.CALL_ASSEMBLER, args,
                                        op.result, op.getdescr()))

    # ----------

    def emitting_an_operation_that_can_collect(self):
        # must be called whenever we emit an operation that can collect:
        # forgets the previous MALLOC_NURSERY, if any; and empty the
        # set 'write_barrier_applied', so that future SETFIELDs will generate
        # a write barrier as usual.
        self._op_malloc_nursery = None
        self.write_barrier_applied.clear()

    def _gen_call_malloc_gc(self, args, v_result, descr):
        """Generate a CALL_MALLOC_GC with the given args."""
        self.emitting_an_operation_that_can_collect()
        op = ResOperation(rop.CALL_MALLOC_GC, args, v_result, descr)
        self.newops.append(op)
        # mark 'v_result' as freshly malloced, so not needing a write barrier
        self.write_barrier_applied[v_result] = None

    def gen_malloc_fixedsize(self, size, typeid, v_result):
        """Generate a CALL_MALLOC_GC(malloc_fixedsize_fn, ...).
        Used on Boehm, and on the framework GC for large fixed-size
        mallocs.  (For all I know this latter case never occurs in
        practice, but better safe than sorry.)
        """
        if self.gc_ll_descr.fielddescr_tid is not None:  # framework GC
            assert (size & (WORD-1)) == 0, "size not aligned?"
            addr = self.gc_ll_descr.get_malloc_fn_addr('malloc_big_fixedsize')
            args = [ConstInt(addr), ConstInt(size), ConstInt(typeid)]
            descr = self.gc_ll_descr.malloc_big_fixedsize_descr
        else:                                            # Boehm
            addr = self.gc_ll_descr.get_malloc_fn_addr('malloc_fixedsize')
            args = [ConstInt(addr), ConstInt(size)]
            descr = self.gc_ll_descr.malloc_fixedsize_descr
        self._gen_call_malloc_gc(args, v_result, descr)

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

    def gen_malloc_nursery_varsize(self, itemsize, v_length, v_result,
                                   arraydescr, kind=FLAG_ARRAY):
        """ itemsize is an int, v_length and v_result are boxes
        """
        gc_descr = self.gc_ll_descr
        if (kind == FLAG_ARRAY and
            (arraydescr.basesize != gc_descr.standard_array_basesize or
             arraydescr.lendescr.offset != gc_descr.standard_array_length_ofs)):
            return False
        self.emitting_an_operation_that_can_collect()
        op = ResOperation(rop.CALL_MALLOC_NURSERY_VARSIZE,
                          [ConstInt(kind), ConstInt(itemsize), v_length],
                          v_result, descr=arraydescr)
        self.newops.append(op)
        self.write_barrier_applied[v_result] = None
        return True

    def gen_malloc_nursery_varsize_frame(self, sizebox, v_result):
        """ Generate CALL_MALLOC_NURSERY_VARSIZE_FRAME
        """
        self.emitting_an_operation_that_can_collect()
        op = ResOperation(rop.CALL_MALLOC_NURSERY_VARSIZE_FRAME,
                          [sizebox],
                          v_result)

        self.newops.append(op)
        self.write_barrier_applied[v_result] = None

    def gen_malloc_nursery(self, size, v_result):
        """Try to generate or update a CALL_MALLOC_NURSERY.
        If that fails, generate a plain CALL_MALLOC_GC instead.
        """
        size = self.round_up_for_allocation(size)
        if not self.gc_ll_descr.can_use_nursery_malloc(size):
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
        self.write_barrier_applied[v_result] = None
        return True

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
        if val not in self.write_barrier_applied:
            v = op.getarg(1)
            if isinstance(v, BoxPtr) or (isinstance(v, ConstPtr) and
                                         bool(v.value)): # store a non-NULL
                self.gen_write_barrier(val)
                #op = op.copy_and_change(rop.SETFIELD_RAW)
        self.newops.append(op)

    def handle_write_barrier_setinteriorfield(self, op):
        val = op.getarg(0)
        if val not in self.write_barrier_applied:
            v = op.getarg(2)
            if isinstance(v, BoxPtr) or (isinstance(v, ConstPtr) and
                                         bool(v.value)): # store a non-NULL
                self.gen_write_barrier(val)
                #op = op.copy_and_change(rop.SETINTERIORFIELD_RAW)
        self.newops.append(op)

    def handle_write_barrier_setarrayitem(self, op):
        val = op.getarg(0)
        if val not in self.write_barrier_applied:
            v = op.getarg(2)
            if isinstance(v, BoxPtr) or (isinstance(v, ConstPtr) and
                                         bool(v.value)): # store a non-NULL
                self.gen_write_barrier_array(val, op.getarg(1))
                #op = op.copy_and_change(rop.SETARRAYITEM_RAW)
        self.newops.append(op)

    def gen_write_barrier(self, v_base):
        write_barrier_descr = self.gc_ll_descr.write_barrier_descr
        args = [v_base]
        self.newops.append(ResOperation(rop.COND_CALL_GC_WB, args, None,
                                        descr=write_barrier_descr))
        self.write_barrier_applied[v_base] = None

    def gen_write_barrier_array(self, v_base, v_index):
        write_barrier_descr = self.gc_ll_descr.write_barrier_descr
        if write_barrier_descr.has_write_barrier_from_array(self.cpu):
            # If we know statically the length of 'v', and it is not too
            # big, then produce a regular write_barrier.  If it's unknown or
            # too big, produce instead a write_barrier_from_array.
            LARGE = 130
            length = self.known_lengths.get(v_base, LARGE)
            if length >= LARGE:
                # unknown or too big: produce a write_barrier_from_array
                args = [v_base, v_index]
                self.newops.append(
                    ResOperation(rop.COND_CALL_GC_WB_ARRAY, args, None,
                                 descr=write_barrier_descr))
                # a WB_ARRAY is not enough to prevent any future write
                # barriers, so don't add to 'write_barrier_applied'!
                return
        # fall-back case: produce a write_barrier
        self.gen_write_barrier(v_base)

    def round_up_for_allocation(self, size):
        if not self.gc_ll_descr.round_up:
            return size
        if self.gc_ll_descr.translate_support_code:
            from rpython.rtyper.lltypesystem import llarena
            return llarena.round_up_for_allocation(
                size, self.gc_ll_descr.minimal_size_in_nursery)
        else:
            # non-translated: do it manually
            # assume that "self.gc_ll_descr.minimal_size_in_nursery" is 2 WORDs
            size = max(size, 2 * WORD)
            return (size + WORD-1) & ~(WORD-1)     # round up
