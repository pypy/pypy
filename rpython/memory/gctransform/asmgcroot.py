from rpython.flowspace.model import (Constant, Variable, Block, Link,
     copygraph, SpaceOperation, checkgraph)
from rpython.rlib.debug import ll_assert
from rpython.rlib.nonconst import NonConstant
from rpython.rlib import rgil
from rpython.rtyper.annlowlevel import llhelper
from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.memory.gctransform.framework import (
     BaseFrameworkGCTransformer, BaseRootWalker)
from rpython.rtyper.llannotation import SomeAddress
from rpython.rtyper.rbuiltin import gen_cast
from rpython.translator.unsimplify import varoftype
from rpython.translator.tool.cbuild import ExternalCompilationInfo
import sys


#
#  This transformer avoids the use of a shadow stack in a completely
#  platform-specific way, by directing genc to insert asm() special
#  instructions in the C source, which are recognized by GCC.
#  The .s file produced by GCC is then parsed by trackgcroot.py.
#

IS_64_BITS = sys.maxint > 2147483647

class AsmGcRootFrameworkGCTransformer(BaseFrameworkGCTransformer):
    _asmgcc_save_restore_arguments = None

    def push_roots(self, hop, keep_current_args=False):
        livevars = self.get_livevars_for_roots(hop, keep_current_args)
        self.num_pushs += len(livevars)
        return livevars

    def pop_roots(self, hop, livevars):
        if not livevars:
            return
        # mark the values as gc roots
        for var in livevars:
            v_adr = gen_cast(hop.llops, llmemory.Address, var)
            v_newaddr = hop.genop("direct_call", [c_asm_gcroot, v_adr],
                                  resulttype=llmemory.Address)
            hop.genop("gc_reload_possibly_moved", [v_newaddr, var])

    def build_root_walker(self):
        return AsmStackRootWalker(self)

    def mark_call_cannotcollect(self, hop, name):
        hop.genop("direct_call", [c_asm_nocollect, name])

    def gct_direct_call(self, hop):
        # just a sanity check: if we find a fnptr with the hint on the
        # _callable, then we'd also find the hint by looking only at the
        # graph.  We'll actually change this graph only later, in
        # start_transforming_graph().
        fnptr = hop.spaceop.args[0].value
        try:
            close_stack = fnptr._obj._callable._gctransformer_hint_close_stack_
        except AttributeError:
            pass
        else:
            assert fnptr._obj.graph.func is fnptr._obj._callable
        BaseFrameworkGCTransformer.gct_direct_call(self, hop)

    def start_transforming_graph(self, graph):
        try:
            close_stack = graph.func._gctransformer_hint_close_stack_
        except AttributeError:
            close_stack = False
        if close_stack:
            self._transform_hint_close_stack(graph)

    def _transform_hint_close_stack(self, graph):
        # We cannot easily pass variable amount of arguments of the call
        # across the call to the pypy_asm_stackwalk helper.  So we store
        # them away and restore them.  More precisely, we need to
        # replace 'graph' with code that saves the arguments, and make
        # a new graph that starts with restoring the arguments.
        if self._asmgcc_save_restore_arguments is None:
            self._asmgcc_save_restore_arguments = {}
        sradict = self._asmgcc_save_restore_arguments
        sra = []     # list of pointers to raw-malloced containers for args
        seen = {}
        ARGS = [v.concretetype for v in graph.getargs()]
        for TYPE in ARGS:
            if isinstance(TYPE, lltype.Ptr):
                TYPE = llmemory.Address
            num = seen.get(TYPE, 0)
            seen[TYPE] = num + 1
            key = (TYPE, num)
            if key not in sradict:
                CONTAINER = lltype.FixedSizeArray(TYPE, 1)
                p = lltype.malloc(CONTAINER, flavor='raw', zero=True,
                                  immortal=True)
                sradict[key] = Constant(p, lltype.Ptr(CONTAINER))
            sra.append(sradict[key])
        #
        # make a copy of the graph that will reload the values
        graph2 = copygraph(graph)
        del graph2.func   # otherwise, start_transforming_graph() will
                          # again transform graph2, and we get an
                          # infinite loop
        #
        # edit the original graph to only store the value of the arguments
        block = Block(graph.startblock.inputargs)
        c_item0 = Constant('item0', lltype.Void)
        assert len(block.inputargs) == len(sra)
        for v_arg, c_p in zip(block.inputargs, sra):
            if isinstance(v_arg.concretetype, lltype.Ptr):
                v_adr = varoftype(llmemory.Address)
                block.operations.append(
                    SpaceOperation("cast_ptr_to_adr", [v_arg], v_adr))
                v_arg = v_adr
            v_void = varoftype(lltype.Void)
            block.operations.append(
                SpaceOperation("bare_setfield", [c_p, c_item0, v_arg], v_void))
        #
        # call asm_stackwalk(graph2)
        RESULT = graph.getreturnvar().concretetype
        FUNC2 = lltype.FuncType([], RESULT)
        fnptr2 = lltype.functionptr(FUNC2,
                                    graph.name + '_reload',
                                    graph=graph2)
        c_fnptr2 = Constant(fnptr2, lltype.Ptr(FUNC2))
        HELPERFUNC = lltype.FuncType([lltype.Ptr(FUNC2),
                                      ASM_FRAMEDATA_HEAD_PTR], RESULT)
        v_asm_stackwalk = varoftype(lltype.Ptr(HELPERFUNC), "asm_stackwalk")
        block.operations.append(
            SpaceOperation("cast_pointer", [c_asm_stackwalk], v_asm_stackwalk))
        v_result = varoftype(RESULT)
        block.operations.append(
            SpaceOperation("indirect_call", [v_asm_stackwalk, c_fnptr2,
                                             c_gcrootanchor,
                                             Constant(None, lltype.Void)],
                           v_result))
        block.closeblock(Link([v_result], graph.returnblock))
        graph.startblock = block
        #
        # edit the copy of the graph to reload the values
        block2 = graph2.startblock
        block1 = Block([])
        reloadedvars = []
        for v, c_p in zip(block2.inputargs, sra):
            v = v.copy()
            if isinstance(v.concretetype, lltype.Ptr):
                w = varoftype(llmemory.Address)
            else:
                w = v
            block1.operations.append(SpaceOperation('getfield',
                                                    [c_p, c_item0], w))
            if w is not v:
                block1.operations.append(SpaceOperation('cast_adr_to_ptr',
                                                        [w], v))
            reloadedvars.append(v)
        block1.closeblock(Link(reloadedvars, block2))
        graph2.startblock = block1
        #
        checkgraph(graph)
        checkgraph(graph2)


class AsmStackRootWalker(BaseRootWalker):

    def __init__(self, gctransformer):
        BaseRootWalker.__init__(self, gctransformer)

        def _asm_callback():
            self.walk_stack_from()
        self._asm_callback = _asm_callback
        self._shape_decompressor = ShapeDecompressor()
        self._with_jit = hasattr(gctransformer.translator, '_jit2gc')
        if self._with_jit:
            jit2gc = gctransformer.translator._jit2gc
            self.frame_tid = jit2gc['frame_tid']
        self.gctransformer = gctransformer
        #
        # unless overridden in need_thread_support():
        self.belongs_to_current_thread = lambda framedata: True

    def need_stacklet_support(self, gctransformer, getfn):
        from rpython.annotator import model as annmodel
        from rpython.rlib import _stacklet_asmgcc
        # stacklet support: BIG HACK for rlib.rstacklet
        _stacklet_asmgcc._asmstackrootwalker = self     # as a global! argh
        _stacklet_asmgcc.complete_destrptr(gctransformer)
        #
        def gc_detach_callback_pieces():
            anchor = llmemory.cast_ptr_to_adr(gcrootanchor)
            result = llmemory.NULL
            framedata = anchor.address[1]
            while framedata != anchor:
                next = framedata.address[1]
                if self.belongs_to_current_thread(framedata):
                    # detach it
                    prev = framedata.address[0]
                    prev.address[1] = next
                    next.address[0] = prev
                    # update the global stack counter
                    rffi.stackcounter.stacks_counter -= 1
                    # reattach framedata into the singly-linked list 'result'
                    framedata.address[0] = rffi.cast(llmemory.Address, -1)
                    framedata.address[1] = result
                    result = framedata
                framedata = next
            return result
        #
        def gc_reattach_callback_pieces(pieces):
            anchor = llmemory.cast_ptr_to_adr(gcrootanchor)
            while pieces != llmemory.NULL:
                framedata = pieces
                pieces = pieces.address[1]
                # attach 'framedata' into the normal doubly-linked list
                following = anchor.address[1]
                following.address[0] = framedata
                framedata.address[1] = following
                anchor.address[1] = framedata
                framedata.address[0] = anchor
                # update the global stack counter
                rffi.stackcounter.stacks_counter += 1
        #
        s_addr = SomeAddress()
        s_None = annmodel.s_None
        self.gc_detach_callback_pieces_ptr = getfn(gc_detach_callback_pieces,
                                                   [], s_addr)
        self.gc_reattach_callback_pieces_ptr=getfn(gc_reattach_callback_pieces,
                                                   [s_addr], s_None)

    def need_thread_support(self, gctransformer, getfn):
        # Threads supported "out of the box" by the rest of the code.
        # The whole code in this function is only there to support
        # fork()ing in a multithreaded process :-(
        # For this, we need to handle gc_thread_start and gc_thread_die
        # to record the mapping {thread_id: stack_start}, and
        # gc_thread_before_fork and gc_thread_after_fork to get rid of
        # all ASM_FRAMEDATA structures that do no belong to the current
        # thread after a fork().
        from rpython.rlib import rthread
        from rpython.memory.support import AddressDict
        from rpython.memory.support import copy_without_null_values
        from rpython.annotator import model as annmodel
        gcdata = self.gcdata

        def get_aid():
            """Return the thread identifier, cast to an (opaque) address."""
            return llmemory.cast_int_to_adr(rthread.get_ident())

        def thread_start():
            value = llmemory.cast_int_to_adr(llop.stack_current(lltype.Signed))
            gcdata.aid2stack.setitem(get_aid(), value)
        thread_start._always_inline_ = True

        def thread_setup():
            gcdata.aid2stack = AddressDict()
            gcdata.dead_threads_count = 0
            # to also register the main thread's stack
            thread_start()
        thread_setup._always_inline_ = True

        def thread_die():
            gcdata.aid2stack.setitem(get_aid(), llmemory.NULL)
            # from time to time, rehash the dictionary to remove
            # old NULL entries
            gcdata.dead_threads_count += 1
            if (gcdata.dead_threads_count & 511) == 0:
                copy = copy_without_null_values(gcdata.aid2stack)
                gcdata.aid2stack.delete()
                gcdata.aid2stack = copy

        def belongs_to_current_thread(framedata):
            # xxx obscure: the answer is Yes if, as a pointer, framedata
            # lies between the start of the current stack and the top of it.
            stack_start = gcdata.aid2stack.get(get_aid(), llmemory.NULL)
            ll_assert(stack_start != llmemory.NULL,
                      "current thread not found in gcdata.aid2stack!")
            stack_stop = llmemory.cast_int_to_adr(
                             llop.stack_current(lltype.Signed))
            return (stack_start <= framedata <= stack_stop or
                    stack_start >= framedata >= stack_stop)
        self.belongs_to_current_thread = belongs_to_current_thread

        def thread_before_fork():
            # before fork(): collect all ASM_FRAMEDATA structures that do
            # not belong to the current thread, and move them out of the
            # way, i.e. out of the main circular doubly linked list.
            detached_pieces = llmemory.NULL
            anchor = llmemory.cast_ptr_to_adr(gcrootanchor)
            initialframedata = anchor.address[1]
            while initialframedata != anchor:   # while we have not looped back
                if not belongs_to_current_thread(initialframedata):
                    # Unlink it
                    prev = initialframedata.address[0]
                    next = initialframedata.address[1]
                    prev.address[1] = next
                    next.address[0] = prev
                    # Link it to the singly linked list 'detached_pieces'
                    initialframedata.address[0] = detached_pieces
                    detached_pieces = initialframedata
                    rffi.stackcounter.stacks_counter -= 1
                # Then proceed to the next piece of stack
                initialframedata = initialframedata.address[1]
            return detached_pieces

        def thread_after_fork(result_of_fork, detached_pieces):
            if result_of_fork == 0:
                # We are in the child process.  Assumes that only the
                # current thread survived.  All the detached_pieces
                # are pointers in other stacks, so have likely been
                # freed already by the multithreaded library.
                # Nothing more for us to do.
                pass
            else:
                # We are still in the parent process.  The fork() may
                # have succeeded or not, but that's irrelevant here.
                # We need to reattach the detached_pieces now, to the
                # circular doubly linked list at 'gcrootanchor'.  The
                # order is not important.
                anchor = llmemory.cast_ptr_to_adr(gcrootanchor)
                while detached_pieces != llmemory.NULL:
                    reattach = detached_pieces
                    detached_pieces = detached_pieces.address[0]
                    a_next = anchor.address[1]
                    reattach.address[0] = anchor
                    reattach.address[1] = a_next
                    anchor.address[1] = reattach
                    a_next.address[0] = reattach
                    rffi.stackcounter.stacks_counter += 1

        self.thread_setup = thread_setup
        self.thread_start_ptr = getfn(thread_start, [], annmodel.s_None,
                                      inline=True)
        self.thread_die_ptr = getfn(thread_die, [], annmodel.s_None)
        self.thread_before_fork_ptr = getfn(thread_before_fork, [],
                                            SomeAddress())
        self.thread_after_fork_ptr = getfn(thread_after_fork,
                                           [annmodel.SomeInteger(),
                                            SomeAddress()],
                                           annmodel.s_None)
        #
        # check that the order of the need_*() is correct for us: if we
        # need both threads and stacklets, need_thread_support() must be
        # called first, to initialize self.belongs_to_current_thread.
        assert not hasattr(self, 'gc_detach_callback_pieces_ptr')

    def postprocess_graph(self, gct, graph, any_inlining):
        pass

    def walk_stack_roots(self, collect_stack_root, is_minor=False):
        gcdata = self.gcdata
        gcdata._gc_collect_stack_root = collect_stack_root
        gcdata._gc_collect_is_minor = is_minor
        pypy_asm_stackwalk(llhelper(ASM_CALLBACK_PTR, self._asm_callback),
                           gcrootanchor)

    def walk_stack_from(self):
        curframe = lltype.malloc(WALKFRAME, flavor='raw')
        otherframe = lltype.malloc(WALKFRAME, flavor='raw')

        # Walk over all the pieces of stack.  They are in a circular linked
        # list of structures of 7 words, the 2 first words being prev/next.
        # The anchor of this linked list is:
        anchor = llmemory.cast_ptr_to_adr(gcrootanchor)
        initialframedata = anchor.address[1]
        stackscount = 0
        while initialframedata != anchor:     # while we have not looped back
            self.walk_frames(curframe, otherframe, initialframedata)
            # Then proceed to the next piece of stack
            initialframedata = initialframedata.address[1]
            stackscount += 1
        #
        # for the JIT: rpy_fastgil may contain an extra framedata
        rpy_fastgil = rgil.gil_fetch_fastgil().signed[0]
        if rpy_fastgil != 1:
            ll_assert(rpy_fastgil != 0, "walk_stack_from doesn't have the GIL")
            initialframedata = rffi.cast(llmemory.Address, rpy_fastgil)
            #
            # very rare issue: initialframedata.address[0] is uninitialized
            # in this case, but "retaddr = callee.frame_address.address[0]"
            # reads it.  If it happens to be exactly a valid return address
            # inside the C code, then bad things occur.
            initialframedata.address[0] = llmemory.NULL
            #
            self.walk_frames(curframe, otherframe, initialframedata)
            stackscount += 1
        #
        expected = rffi.stackcounter.stacks_counter
        if NonConstant(0):
            rffi.stackcounter.stacks_counter += 42    # hack to force it
        ll_assert(not (stackscount < expected), "non-closed stacks around")
        ll_assert(not (stackscount > expected), "stacks counter corruption?")
        lltype.free(otherframe, flavor='raw')
        lltype.free(curframe, flavor='raw')

    def walk_frames(self, curframe, otherframe, initialframedata):
        self.fill_initial_frame(curframe, initialframedata)
        # Loop over all the frames in the stack
        while self.walk_to_parent_frame(curframe, otherframe):
            swap = curframe
            curframe = otherframe    # caller becomes callee
            otherframe = swap

    def fill_initial_frame(self, curframe, initialframedata):
        # Read the information provided by initialframedata
        initialframedata += 2*sizeofaddr #skip the prev/next words at the start
        reg = 0
        while reg < CALLEE_SAVED_REGS:
            # NB. 'initialframedata' stores the actual values of the
            # registers %ebx etc., and if these values are modified
            # they are reloaded by pypy_asm_stackwalk().  By contrast,
            # 'regs_stored_at' merely points to the actual values
            # from the 'initialframedata'.
            curframe.regs_stored_at[reg] = initialframedata + reg*sizeofaddr
            reg += 1
        curframe.frame_address = initialframedata.address[CALLEE_SAVED_REGS]

    def walk_to_parent_frame(self, callee, caller):
        """Starting from 'callee', walk the next older frame on the stack
        and fill 'caller' accordingly.  Also invokes the collect_stack_root()
        callback from the GC code for each GC root found in 'caller'.
        """
        #
        # The gcmap table is a list of entries, two machine words each:
        #     void *SafePointAddress;
        #     int Shape;
        #
        # A "safe point" is the return address of a call.
        # The "shape" of a safe point is a list of integers
        # that represent "locations".  A "location" can be
        # either in the stack or in a register.  See
        # getlocation() for the decoding of this integer.
        # The locations stored in a "shape" are as follows:
        #
        #   * The "location" of the return address.  This is just
        #     after the end of the frame of 'callee'; it is the
        #     first word of the frame of 'caller' (see picture
        #     below).
        #
        #   * Four "locations" that specify where the function saves
        #     each of the four callee-saved registers (%ebx, %esi,
        #     %edi, %ebp).
        #
        #   * The number of live GC roots around the call.
        #
        #   * For each GC root, an integer that specify where the
        #     GC pointer is stored.  This is a "location" too.
        #
        # XXX the details are completely specific to X86!!!
        # a picture of the stack may help:
        #                                           ^ ^ ^
        #     |     ...      |                 to older frames
        #     +--------------+
        #     |   ret addr   |  <------ caller_frame (addr of retaddr)
        #     |     ...      |
        #     | caller frame |
        #     |     ...      |
        #     +--------------+
        #     |   ret addr   |  <------ callee_frame (addr of retaddr)
        #     |     ...      |
        #     | callee frame |
        #     |     ...      |                 lower addresses
        #     +--------------+                      v v v
        #

        retaddr = callee.frame_address.address[0]
        #
        # try to locate the caller function based on retaddr.
        # set up self._shape_decompressor.
        #
        ebp_in_caller = callee.regs_stored_at[INDEX_OF_EBP].address[0]
        self.locate_caller_based_on_retaddr(retaddr, ebp_in_caller)
        #
        # found!  Enumerate the GC roots in the caller frame
        #
        collect_stack_root = self.gcdata._gc_collect_stack_root
        gc = self.gc
        while True:
            location = self._shape_decompressor.next()
            if location == 0:
                break
            addr = self.getlocation(callee, ebp_in_caller, location)
            if gc.points_to_valid_gc_object(addr):
                collect_stack_root(gc, addr)
        #
        # small hack: the JIT reserves THREADLOCAL_OFS's last bit for
        # us.  We use it to store an "already traced past this frame"
        # flag.
        if self._with_jit and self.gcdata._gc_collect_is_minor:
            if self.mark_jit_frame_can_stop(callee):
                return False
        #
        # track where the caller_frame saved the registers from its own
        # caller
        #
        reg = CALLEE_SAVED_REGS - 1
        while reg >= 0:
            location = self._shape_decompressor.next()
            addr = self.getlocation(callee, ebp_in_caller, location)
            caller.regs_stored_at[reg] = addr
            reg -= 1

        location = self._shape_decompressor.next()
        caller.frame_address = self.getlocation(callee, ebp_in_caller,
                                                location)
        # we get a NULL marker to mean "I'm the frame
        # of the entry point, stop walking"
        return caller.frame_address != llmemory.NULL

    def locate_caller_based_on_retaddr(self, retaddr, ebp_in_caller):
        gcmapstart = llop.gc_asmgcroot_static(llmemory.Address, 0)
        gcmapend   = llop.gc_asmgcroot_static(llmemory.Address, 1)
        item = search_in_gcmap(gcmapstart, gcmapend, retaddr)
        if item:
            self._shape_decompressor.setpos(item.signed[1])
            return

        if not self._shape_decompressor.sorted:
            # the item may have been not found because the main array was
            # not sorted.  Sort it and try again.
            win32_follow_gcmap_jmp(gcmapstart, gcmapend)
            sort_gcmap(gcmapstart, gcmapend)
            self._shape_decompressor.sorted = True
            item = search_in_gcmap(gcmapstart, gcmapend, retaddr)
            if item:
                self._shape_decompressor.setpos(item.signed[1])
                return

        if self._with_jit:
            # item not found.  We assume that it's a JIT-generated
            # location -- but we check for consistency that ebp points
            # to a JITFRAME object.
            from rpython.jit.backend.llsupport.jitframe import STACK_DEPTH_OFS

            tid = self.gc.get_possibly_forwarded_type_id(ebp_in_caller)
            if (rffi.cast(lltype.Signed, tid) ==
                    rffi.cast(lltype.Signed, self.frame_tid)):
                # fish the depth
                extra_stack_depth = (ebp_in_caller + STACK_DEPTH_OFS).signed[0]
                ll_assert((extra_stack_depth & (rffi.sizeof(lltype.Signed) - 1))
                           == 0, "asmgcc: misaligned extra_stack_depth")
                extra_stack_depth //= rffi.sizeof(lltype.Signed)
                self._shape_decompressor.setjitframe(extra_stack_depth)
                return
        llop.debug_fatalerror(lltype.Void, "cannot find gc roots!")

    def getlocation(self, callee, ebp_in_caller, location):
        """Get the location in the 'caller' frame of a variable, based
        on the integer 'location' that describes it.  All locations are
        computed based on information saved by the 'callee'.
        """
        ll_assert(location >= 0, "negative location")
        kind = location & LOC_MASK
        offset = location & ~ LOC_MASK
        if IS_64_BITS:
            offset <<= 1
        if kind == LOC_REG:   # register
            if location == LOC_NOWHERE:
                return llmemory.NULL
            reg = (location >> 2) - 1
            ll_assert(reg < CALLEE_SAVED_REGS, "bad register location")
            return callee.regs_stored_at[reg]
        elif kind == LOC_ESP_PLUS:    # in the caller stack frame at N(%esp)
            esp_in_caller = callee.frame_address + sizeofaddr
            return esp_in_caller + offset
        elif kind == LOC_EBP_PLUS:    # in the caller stack frame at N(%ebp)
            return ebp_in_caller + offset
        else:  # kind == LOC_EBP_MINUS:   at -N(%ebp)
            return ebp_in_caller - offset

    def mark_jit_frame_can_stop(self, callee):
        location = self._shape_decompressor.get_threadlocal_loc()
        if location == LOC_NOWHERE:
            return False
        addr = self.getlocation(callee, llmemory.NULL, location)
        #
        x = addr.signed[0]
        if x & 1:
            return True            # this JIT stack frame is already marked!
        else:
            addr.signed[0] = x | 1    # otherwise, mark it but don't stop
            return False


LOC_REG       = 0
LOC_ESP_PLUS  = 1
LOC_EBP_PLUS  = 2
LOC_EBP_MINUS = 3
LOC_MASK      = 0x03
LOC_NOWHERE   = LOC_REG | 0

# ____________________________________________________________

sizeofaddr = llmemory.sizeof(llmemory.Address)
arrayitemsize = 2 * sizeofaddr


def binary_search(start, end, addr1):
    """Search for an element in a sorted array.

    The interval from the start address (included) to the end address
    (excluded) is assumed to be a sorted arrays of pairs (addr1, addr2).
    This searches for the item with a given addr1 and returns its
    address.  If not found exactly, it tries to return the address
    of the item left of addr1 (i.e. such that result.address[0] < addr1).
    """
    count = (end - start) // arrayitemsize
    while count > 1:
        middleindex = count // 2
        middle = start + middleindex * arrayitemsize
        if addr1 < middle.address[0]:
            count = middleindex
        else:
            start = middle
            count -= middleindex
    return start

def search_in_gcmap(gcmapstart, gcmapend, retaddr):
    item = binary_search(gcmapstart, gcmapend, retaddr)
    if item.address[0] == retaddr:
        return item     # found
    # 'retaddr' not exactly found.  Check that 'item' is the start of a
    # compressed range that includes 'retaddr'.
    if retaddr > item.address[0] and item.signed[1] < 0:
        return item     # ok
    else:
        return llmemory.NULL    # failed

def search_in_gcmap2(gcmapstart, gcmapend, retaddr):
    # same as 'search_in_gcmap', but without range checking support
    # (item.signed[1] is an address in this case, not a signed at all!)
    item = binary_search(gcmapstart, gcmapend, retaddr)
    if item.address[0] == retaddr:
        return item.address[1]     # found
    else:
        return llmemory.NULL    # failed

def sort_gcmap(gcmapstart, gcmapend):
    count = (gcmapend - gcmapstart) // arrayitemsize
    qsort(gcmapstart,
          rffi.cast(rffi.SIZE_T, count),
          rffi.cast(rffi.SIZE_T, arrayitemsize),
          c_compare_gcmap_entries)

def replace_dead_entries_with_nulls(start, end):
    # replace the dead entries (null value) with a null key.
    count = (end - start) // arrayitemsize - 1
    while count >= 0:
        item = start + count * arrayitemsize
        if item.address[1] == llmemory.NULL:
            item.address[0] = llmemory.NULL
        count -= 1

if sys.platform == 'win32':
    def win32_follow_gcmap_jmp(start, end):
        # The initial gcmap table contains addresses to a JMP
        # instruction that jumps indirectly to the real code.
        # Replace them with the target addresses.
        assert rffi.SIGNEDP is rffi.LONGP, "win64 support missing"
        while start < end:
            code = rffi.cast(rffi.CCHARP, start.address[0])[0]
            if code == '\xe9': # jmp
                rel32 = rffi.cast(rffi.SIGNEDP, start.address[0]+1)[0]
                target = start.address[0] + (rel32 + 5)
                start.address[0] = target
            start += arrayitemsize
else:
    def win32_follow_gcmap_jmp(start, end):
        pass

# ____________________________________________________________

class ShapeDecompressor:
    _alloc_flavor_ = "raw"

    sorted = False

    def setpos(self, pos):
        if pos < 0:
            pos = ~ pos     # can ignore this "range" marker here
        gccallshapes = llop.gc_asmgcroot_static(llmemory.Address, 2)
        self.addr = gccallshapes + pos
        self.jit_index = -1

    def setjitframe(self, extra_stack_depth):
        self.jit_index = 0
        self.extra_stack_depth = extra_stack_depth

    def next(self):
        index = self.jit_index
        if index < 0:
            # case "outside the jit"
            addr = self.addr
            value = 0
            while True:
                b = ord(addr.char[0])
                addr += 1
                value += b
                if b < 0x80:
                    break
                value = (value - 0x80) << 7
            self.addr = addr
            return value
        else:
            # case "in the jit"
            from rpython.jit.backend.x86.arch import FRAME_FIXED_SIZE
            from rpython.jit.backend.x86.arch import PASS_ON_MY_FRAME
            self.jit_index = index + 1
            if index == 0:
                # the jitframe is an object in EBP
                return LOC_REG | ((INDEX_OF_EBP + 1) << 2)
            if index == 1:
                return 0
            # the remaining returned values should be:
            #      saved %rbp
            #      saved %r15           or on 32bit:
            #      saved %r14             saved %ebp
            #      saved %r13             saved %edi
            #      saved %r12             saved %esi
            #      saved %rbx             saved %ebx
            #      return addr            return addr
            stack_depth = PASS_ON_MY_FRAME + self.extra_stack_depth
            if IS_64_BITS:
                if index == 2:   # rbp
                    return LOC_ESP_PLUS | (stack_depth << 2)
                if index == 3:   # r15
                    return LOC_ESP_PLUS | ((stack_depth + 5) << 2)
                if index == 4:   # r14
                    return LOC_ESP_PLUS | ((stack_depth + 4) << 2)
                if index == 5:   # r13
                    return LOC_ESP_PLUS | ((stack_depth + 3) << 2)
                if index == 6:   # r12
                    return LOC_ESP_PLUS | ((stack_depth + 2) << 2)
                if index == 7:   # rbx
                    return LOC_ESP_PLUS | ((stack_depth + 1) << 2)
                if index == 8:   # return addr
                    return (LOC_ESP_PLUS |
                        ((FRAME_FIXED_SIZE + self.extra_stack_depth) << 2))
            else:
                if index == 2:   # ebp
                    return LOC_ESP_PLUS | (stack_depth << 2)
                if index == 3:   # edi
                    return LOC_ESP_PLUS | ((stack_depth + 3) << 2)
                if index == 4:   # esi
                    return LOC_ESP_PLUS | ((stack_depth + 2) << 2)
                if index == 5:   # ebx
                    return LOC_ESP_PLUS | ((stack_depth + 1) << 2)
                if index == 6:   # return addr
                    return (LOC_ESP_PLUS |
                        ((FRAME_FIXED_SIZE + self.extra_stack_depth) << 2))
            llop.debug_fatalerror(lltype.Void, "asmgcroot: invalid index")
            return 0   # annotator fix

    def get_threadlocal_loc(self):
        index = self.jit_index
        if index < 0:
            return LOC_NOWHERE     # case "outside the jit"
        else:
            # case "in the jit"
            from rpython.jit.backend.x86.arch import THREADLOCAL_OFS, WORD
            return (LOC_ESP_PLUS |
                    ((THREADLOCAL_OFS // WORD + self.extra_stack_depth) << 2))


# ____________________________________________________________

#
# The special pypy_asm_stackwalk(), implemented directly in
# assembler, fills information about the current stack top in an
# ASM_FRAMEDATA array and invokes an RPython callback with it.
# An ASM_FRAMEDATA is an array of 5 values that describe everything
# we need to know about a stack frame:
#
#   - the value that %ebx had when the current function started
#   - the value that %esi had when the current function started
#   - the value that %edi had when the current function started
#   - the value that %ebp had when the current function started
#   - frame address (actually the addr of the retaddr of the current function;
#                    that's the last word of the frame in memory)
#
# On 64 bits, it is an array of 7 values instead of 5:
#
#   - %rbx, %r12, %r13, %r14, %r15, %rbp; and the frame address
#

if IS_64_BITS:
    CALLEE_SAVED_REGS = 6
    INDEX_OF_EBP      = 5
    FRAME_PTR         = CALLEE_SAVED_REGS
else:
    CALLEE_SAVED_REGS = 4       # there are 4 callee-saved registers
    INDEX_OF_EBP      = 3
    FRAME_PTR         = CALLEE_SAVED_REGS    # the frame is at index 4 in the array

JIT_USE_WORDS = 2 + FRAME_PTR + 1

ASM_CALLBACK_PTR = lltype.Ptr(lltype.FuncType([], lltype.Void))

# used internally by walk_stack_from()
WALKFRAME = lltype.Struct('WALKFRAME',
        ('regs_stored_at',    # address of where the registers have been saved
             lltype.FixedSizeArray(llmemory.Address, CALLEE_SAVED_REGS)),
        ('frame_address',
             llmemory.Address),
    )

# We have a circular doubly-linked list of all the ASM_FRAMEDATAs currently
# alive.  The list's starting point is given by 'gcrootanchor', which is not
# a full ASM_FRAMEDATA but only contains the prev/next pointers:
ASM_FRAMEDATA_HEAD_PTR = lltype.Ptr(lltype.ForwardReference())
ASM_FRAMEDATA_HEAD_PTR.TO.become(lltype.Struct('ASM_FRAMEDATA_HEAD',
        ('prev', ASM_FRAMEDATA_HEAD_PTR),
        ('next', ASM_FRAMEDATA_HEAD_PTR)
    ))
gcrootanchor = lltype.malloc(ASM_FRAMEDATA_HEAD_PTR.TO, immortal=True)
gcrootanchor.prev = gcrootanchor
gcrootanchor.next = gcrootanchor
c_gcrootanchor = Constant(gcrootanchor, ASM_FRAMEDATA_HEAD_PTR)

eci = ExternalCompilationInfo(compile_extra=['-DPYPY_USE_ASMGCC'],
                              post_include_bits=["""
static int pypy_compare_gcmap_entries(const void *addr1, const void *addr2)
{
    char *key1 = * (char * const *) addr1;
    char *key2 = * (char * const *) addr2;
    if (key1 < key2)
        return -1;
    else if (key1 == key2)
        return 0;
    else
        return 1;
}
"""])

pypy_asm_stackwalk = rffi.llexternal('pypy_asm_stackwalk',
                                     [ASM_CALLBACK_PTR,
                                      ASM_FRAMEDATA_HEAD_PTR],
                                     lltype.Signed,
                                     sandboxsafe=True,
                                     _nowrapper=True,
                                     random_effects_on_gcobjs=True,
                                     compilation_info=eci)
c_asm_stackwalk = Constant(pypy_asm_stackwalk,
                           lltype.typeOf(pypy_asm_stackwalk))

pypy_asm_gcroot = rffi.llexternal('pypy_asm_gcroot',
                                  [llmemory.Address],
                                  llmemory.Address,
                                  sandboxsafe=True,
                                  _nowrapper=True)
c_asm_gcroot = Constant(pypy_asm_gcroot, lltype.typeOf(pypy_asm_gcroot))

pypy_asm_nocollect = rffi.llexternal('pypy_asm_gc_nocollect',
                                     [rffi.CCHARP], lltype.Void,
                                     sandboxsafe=True,
                                     _nowrapper=True)
c_asm_nocollect = Constant(pypy_asm_nocollect, lltype.typeOf(pypy_asm_nocollect))

QSORT_CALLBACK_PTR = lltype.Ptr(lltype.FuncType([llmemory.Address,
                                                 llmemory.Address], rffi.INT))
c_compare_gcmap_entries = rffi.llexternal('pypy_compare_gcmap_entries',
                                          [llmemory.Address, llmemory.Address],
                                          rffi.INT, compilation_info=eci,
                                          _nowrapper=True, sandboxsafe=True)
qsort = rffi.llexternal('qsort',
                        [llmemory.Address,
                         rffi.SIZE_T,
                         rffi.SIZE_T,
                         QSORT_CALLBACK_PTR],
                        lltype.Void,
                        sandboxsafe=True,
                        random_effects_on_gcobjs=False,  # but has a callback
                        _nowrapper=True)
