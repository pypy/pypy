from pypy.rpython.memory.gctransform.framework import FrameworkGCTransformer
from pypy.rpython.memory.gctransform.framework import BaseRootWalker
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython.rbuiltin import gen_cast
from pypy.rpython.annlowlevel import llhelper
from pypy.objspace.flow.model import Constant, Variable, Block, Link, copygraph
from pypy.objspace.flow.model import SpaceOperation
from pypy.translator.unsimplify import copyvar
from pypy.rlib.debug import ll_assert
import sys


#
#  This transformer avoids the use of a shadow stack in a completely
#  platform-specific way, by directing genc to insert asm() special
#  instructions in the C source, which are recognized by GCC.
#  The .s file produced by GCC is then parsed by trackgcroot.py.
#

IS_64_BITS = sys.maxint > 2147483647

class AsmGcRootFrameworkGCTransformer(FrameworkGCTransformer):
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
        fnptr = hop.spaceop.args[0].value
        try:
            close_stack = fnptr._obj._callable._gctransformer_hint_close_stack_
        except AttributeError:
            close_stack = False
        if close_stack:
            self.handle_call_with_close_stack(hop)
        else:
            FrameworkGCTransformer.gct_direct_call(self, hop)

    def handle_call_with_close_stack(self, hop):
        fnptr = hop.spaceop.args[0].value
        # We cannot easily pass variable amount of arguments of the call
        # across the call to the pypy_asm_stackwalk helper.  So we store
        # them away and restore them.  We need to make a new graph
        # that starts with restoring the arguments.
        if self._asmgcc_save_restore_arguments is None:
            self._asmgcc_save_restore_arguments = {}
        sradict = self._asmgcc_save_restore_arguments
        sra = []     # list of pointers to raw-malloced containers for args
        seen = {}
        FUNC1 = lltype.typeOf(fnptr).TO
        for TYPE in FUNC1.ARGS:
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
        # store the value of the arguments
        livevars = self.push_roots(hop)
        c_item0 = Constant('item0', lltype.Void)
        for v_arg, c_p in zip(hop.spaceop.args[1:], sra):
            if isinstance(v_arg.concretetype, lltype.Ptr):
                v_arg = hop.genop("cast_ptr_to_adr", [v_arg],
                                  resulttype=llmemory.Address)
            hop.genop("bare_setfield", [c_p, c_item0, v_arg])
        #
        # make a copy of the graph that will reload the values
        graph2 = copygraph(fnptr._obj.graph)
        block2 = graph2.startblock
        block2.isstartblock = False
        block1 = Block([])
        reloadedvars = []
        for v, c_p in zip(block2.inputargs, sra):
            v = copyvar(None, v)
            if isinstance(v.concretetype, lltype.Ptr):
                w = Variable('tmp')
                w.concretetype = llmemory.Address
            else:
                w = v
            block1.operations.append(SpaceOperation('getfield',
                                                    [c_p, c_item0], w))
            if w is not v:
                block1.operations.append(SpaceOperation('cast_adr_to_ptr',
                                                        [w], v))
            reloadedvars.append(v)
        block1.closeblock(Link(reloadedvars, block2))
        block1.isstartblock = True
        graph2.startblock = block1
        FUNC2 = lltype.FuncType([], FUNC1.RESULT)
        fnptr2 = lltype.functionptr(FUNC2,
                                    fnptr._obj._name + '_reload',
                                    graph=graph2)
        c_fnptr2 = Constant(fnptr2, lltype.Ptr(FUNC2))
        HELPERFUNC = lltype.FuncType([lltype.Ptr(FUNC2),
                                      ASM_FRAMEDATA_HEAD_PTR], FUNC1.RESULT)
        #
        v_asm_stackwalk = hop.genop("cast_pointer", [c_asm_stackwalk],
                                    resulttype=lltype.Ptr(HELPERFUNC))
        hop.genop("indirect_call",
                  [v_asm_stackwalk, c_fnptr2, c_gcrootanchor,
                   Constant(None, lltype.Void)],
                  resultvar=hop.spaceop.result)
        self.pop_roots(hop, livevars)


class AsmStackRootWalker(BaseRootWalker):

    def __init__(self, gctransformer):
        BaseRootWalker.__init__(self, gctransformer)

        def _asm_callback():
            self.walk_stack_from()
        self._asm_callback = _asm_callback
        self._shape_decompressor = ShapeDecompressor()
        if hasattr(gctransformer.translator, '_jit2gc'):
            jit2gc = gctransformer.translator._jit2gc
            self._extra_gcmapstart  = jit2gc['gcmapstart']
            self._extra_gcmapend    = jit2gc['gcmapend']
            self._extra_mark_sorted = jit2gc['gcmarksorted']
        else:
            self._extra_gcmapstart  = lambda: llmemory.NULL
            self._extra_gcmapend    = lambda: llmemory.NULL
            self._extra_mark_sorted = lambda: True

    def need_stacklet_support(self, gctransformer, getfn):
        # stacklet support: BIG HACK for rlib.rstacklet
        from pypy.rlib import _stacklet_asmgcc
        _stacklet_asmgcc._asmstackrootwalker = self     # as a global! argh

    def need_thread_support(self, gctransformer, getfn):
        # Threads supported "out of the box" by the rest of the code.
        # The whole code in this function is only there to support
        # fork()ing in a multithreaded process :-(
        # For this, we need to handle gc_thread_start and gc_thread_die
        # to record the mapping {thread_id: stack_start}, and
        # gc_thread_before_fork and gc_thread_after_fork to get rid of
        # all ASM_FRAMEDATA structures that do no belong to the current
        # thread after a fork().
        from pypy.module.thread import ll_thread
        from pypy.rpython.memory.support import AddressDict
        from pypy.rpython.memory.support import copy_without_null_values
        from pypy.annotation import model as annmodel
        gcdata = self.gcdata

        def get_aid():
            """Return the thread identifier, cast to an (opaque) address."""
            return llmemory.cast_int_to_adr(ll_thread.get_ident())

        def thread_start():
            value = llop.stack_current(llmemory.Address)
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
            stack_stop  = llop.stack_current(llmemory.Address)
            return (stack_start <= framedata <= stack_stop or
                    stack_start >= framedata >= stack_stop)

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
                                            annmodel.SomeAddress())
        self.thread_after_fork_ptr = getfn(thread_after_fork,
                                           [annmodel.SomeInteger(),
                                            annmodel.SomeAddress()],
                                           annmodel.s_None)

    def walk_stack_roots(self, collect_stack_root):
        gcdata = self.gcdata
        gcdata._gc_collect_stack_root = collect_stack_root
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
            self.fill_initial_frame(curframe, initialframedata)
            # Loop over all the frames in the stack
            while self.walk_to_parent_frame(curframe, otherframe):
                swap = curframe
                curframe = otherframe    # caller becomes callee
                otherframe = swap
            # Then proceed to the next piece of stack
            initialframedata = initialframedata.address[1]
            stackscount += 1
        #
        expected = rffi.stackcounter.stacks_counter
        ll_assert(not (stackscount < expected), "non-closed stacks around")
        ll_assert(not (stackscount > expected), "stacks counter corruption?")
        lltype.free(otherframe, flavor='raw')
        lltype.free(curframe, flavor='raw')

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
        self.locate_caller_based_on_retaddr(retaddr)
        #
        # found!  Enumerate the GC roots in the caller frame
        #
        collect_stack_root = self.gcdata._gc_collect_stack_root
        ebp_in_caller = callee.regs_stored_at[INDEX_OF_EBP].address[0]
        gc = self.gc
        while True:
            location = self._shape_decompressor.next()
            if location == 0:
                break
            addr = self.getlocation(callee, ebp_in_caller, location)
            if gc.points_to_valid_gc_object(addr):
                collect_stack_root(gc, addr)
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

    def locate_caller_based_on_retaddr(self, retaddr):
        gcmapstart = llop.gc_asmgcroot_static(llmemory.Address, 0)
        gcmapend   = llop.gc_asmgcroot_static(llmemory.Address, 1)
        item = search_in_gcmap(gcmapstart, gcmapend, retaddr)
        if item:
            self._shape_decompressor.setpos(item.signed[1])
            return
        gcmapstart2 = self._extra_gcmapstart()
        gcmapend2   = self._extra_gcmapend()
        if gcmapstart2 != gcmapend2:
            # we have a non-empty JIT-produced table to look in
            item = search_in_gcmap2(gcmapstart2, gcmapend2, retaddr)
            if item:
                self._shape_decompressor.setaddr(item)
                return
            # maybe the JIT-produced table is not sorted?
            was_already_sorted = self._extra_mark_sorted()
            if not was_already_sorted:
                sort_gcmap(gcmapstart2, gcmapend2)
                item = search_in_gcmap2(gcmapstart2, gcmapend2, retaddr)
                if item:
                    self._shape_decompressor.setaddr(item)
                    return
            # there is a rare risk that the array contains *two* entries
            # with the same key, one of which is dead (null value), and we
            # found the dead one above.  Solve this case by replacing all
            # dead keys with nulls, sorting again, and then trying again.
            replace_dead_entries_with_nulls(gcmapstart2, gcmapend2)
            sort_gcmap(gcmapstart2, gcmapend2)
            item = search_in_gcmap2(gcmapstart2, gcmapend2, retaddr)
            if item:
                self._shape_decompressor.setaddr(item)
                return
        # the item may have been not found because the main array was
        # not sorted.  Sort it and try again.
        win32_follow_gcmap_jmp(gcmapstart, gcmapend)
        sort_gcmap(gcmapstart, gcmapend)
        item = search_in_gcmap(gcmapstart, gcmapend, retaddr)
        if item:
            self._shape_decompressor.setpos(item.signed[1])
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
          llhelper(QSORT_CALLBACK_PTR, _compare_gcmap_entries))

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

def _compare_gcmap_entries(addr1, addr2):
    key1 = addr1.address[0]
    key2 = addr2.address[0]
    if key1 < key2:
        result = -1
    elif key1 == key2:
        result = 0
    else:
        result = 1
    return rffi.cast(rffi.INT, result)

# ____________________________________________________________

class ShapeDecompressor:
    _alloc_flavor_ = "raw"

    def setpos(self, pos):
        if pos < 0:
            pos = ~ pos     # can ignore this "range" marker here
        gccallshapes = llop.gc_asmgcroot_static(llmemory.Address, 2)
        self.addr = gccallshapes + pos

    def setaddr(self, addr):
        self.addr = addr

    def next(self):
        value = 0
        addr = self.addr
        while True:
            b = ord(addr.char[0])
            addr += 1
            value += b
            if b < 0x80:
                break
            value = (value - 0x80) << 7
        self.addr = addr
        return value

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

if IS_64_BITS:
    CALLEE_SAVED_REGS = 6
    INDEX_OF_EBP      = 5
    FRAME_PTR         = CALLEE_SAVED_REGS
else:
    CALLEE_SAVED_REGS = 4       # there are 4 callee-saved registers
    INDEX_OF_EBP      = 3
    FRAME_PTR         = CALLEE_SAVED_REGS    # the frame is at index 4 in the array

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

pypy_asm_stackwalk = rffi.llexternal('pypy_asm_stackwalk',
                                     [ASM_CALLBACK_PTR,
                                      ASM_FRAMEDATA_HEAD_PTR],
                                     lltype.Signed,
                                     sandboxsafe=True,
                                     _nowrapper=True,
                                     random_effects_on_gcobjs=True)
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
qsort = rffi.llexternal('qsort',
                        [llmemory.Address,
                         rffi.SIZE_T,
                         rffi.SIZE_T,
                         QSORT_CALLBACK_PTR],
                        lltype.Void,
                        sandboxsafe=True,
                        random_effects_on_gcobjs=False,  # but has a callback
                        _nowrapper=True)
