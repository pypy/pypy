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
                p = lltype.malloc(CONTAINER, flavor='raw', zero=True)
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
        HELPERFUNC = lltype.FuncType([lltype.Ptr(FUNC2)], FUNC1.RESULT)
        #
        v_asm_stackwalk = hop.genop("cast_pointer", [c_asm_stackwalk],
                                    resulttype=lltype.Ptr(HELPERFUNC))
        hop.genop("indirect_call",
                  [v_asm_stackwalk, c_fnptr2, Constant(None, lltype.Void)],
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
            self._extra_gcmapstart = jit2gc['gcmapstart']
            self._extra_gcmapend   = jit2gc['gcmapend']
        else:
            returns_null = lambda: llmemory.NULL
            self._extra_gcmapstart = returns_null
            self._extra_gcmapend   = returns_null

    def need_thread_support(self, gctransformer, getfn):
        # Threads supported "out of the box" by the rest of the code.
        # In particular, we can ignore the gc_thread_prepare,
        # gc_thread_run and gc_thread_die operations.
        pass

    def walk_stack_roots(self, collect_stack_root):
        gcdata = self.gcdata
        gcdata._gc_collect_stack_root = collect_stack_root
        pypy_asm_stackwalk(llhelper(ASM_CALLBACK_PTR, self._asm_callback))

    def walk_stack_from(self):
        curframe = lltype.malloc(WALKFRAME, flavor='raw')
        otherframe = lltype.malloc(WALKFRAME, flavor='raw')

        # Walk over all the pieces of stack.  They are in a circular linked
        # list of structures of 7 words, the 2 first words being prev/next.
        # The anchor of this linked list is:
        anchor = llop.gc_asmgcroot_static(llmemory.Address, 3)
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
        gc = self.gc
        while True:
            location = self._shape_decompressor.next()
            if location == 0:
                break
            addr = self.getlocation(callee, location)
            if gc.points_to_valid_gc_object(addr):
                collect_stack_root(gc, addr)
        #
        # track where the caller_frame saved the registers from its own
        # caller
        #
        reg = CALLEE_SAVED_REGS - 1
        while reg >= 0:
            location = self._shape_decompressor.next()
            addr = self.getlocation(callee, location)
            caller.regs_stored_at[reg] = addr
            reg -= 1

        location = self._shape_decompressor.next()
        caller.frame_address = self.getlocation(callee, location)
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
                self._shape_decompressor.setaddr(item.address[1])
                return
            # maybe the JIT-produced table is not sorted?
            sort_gcmap(gcmapstart2, gcmapend2)
            item = search_in_gcmap2(gcmapstart2, gcmapend2, retaddr)
            if item:
                self._shape_decompressor.setaddr(item.address[1])
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

    def getlocation(self, callee, location):
        """Get the location in the 'caller' frame of a variable, based
        on the integer 'location' that describes it.  All locations are
        computed based on information saved by the 'callee'.
        """
        kind = location & LOC_MASK
        if kind == LOC_REG:   # register
            reg = location >> 2
            ll_assert(0 <= reg < CALLEE_SAVED_REGS, "bad register location")
            return callee.regs_stored_at[reg]
        elif kind == LOC_ESP_BASED:   # in the caller stack frame at N(%esp)
            offset = location & ~ LOC_MASK
            ll_assert(offset >= 0, "bad %esp-based location")
            esp_in_caller = callee.frame_address + 4
            return esp_in_caller + offset
        elif kind == LOC_EBP_BASED:   # in the caller stack frame at N(%ebp)
            offset = location & ~ LOC_MASK
            ebp_in_caller = callee.regs_stored_at[INDEX_OF_EBP].address[0]
            return ebp_in_caller + offset
        else:
            return llmemory.NULL


LOC_NOWHERE   = 0
LOC_REG       = 1
LOC_EBP_BASED = 2
LOC_ESP_BASED = 3
LOC_MASK      = 0x03

# ____________________________________________________________

sizeofaddr = llmemory.sizeof(llmemory.Address)
arrayitemsize = 2 * sizeofaddr


def binary_search(start, end, addr1):
    """Search for an element in a sorted array.

    The interval from the start address (included) to the end address
    (excluded) is assumed to be a sorted arrays of pairs (addr1, addr2).
    This searches for the item with a given addr1 and returns its
    address.
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
        return item     # found
    else:
        return llmemory.NULL    # failed

def sort_gcmap(gcmapstart, gcmapend):
    count = (gcmapend - gcmapstart) // arrayitemsize
    qsort(gcmapstart,
          rffi.cast(rffi.SIZE_T, count),
          rffi.cast(rffi.SIZE_T, arrayitemsize),
          llhelper(QSORT_CALLBACK_PTR, _compare_gcmap_entries))

if sys.platform == 'win32':
    def win32_follow_gcmap_jmp(start, end):
        # The initial gcmap table contains addresses to a JMP
        # instruction that jumps indirectly to the real code.
        # Replace them with the target addresses.
        while start < end:
            code = rffi.cast(rffi.CCHARP, start.address[0])[0]
            if code == '\xe9': # jmp
                rel32 = rffi.cast(rffi.LONGP, start.address[0]+1)[0]
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
        return -1
    elif key1 == key2:
        return 0
    else:
        return 1

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
        if value & 1:
            value = ~ value
        value = value >> 1
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

pypy_asm_stackwalk = rffi.llexternal('pypy_asm_stackwalk',
                                     [ASM_CALLBACK_PTR],
                                     lltype.Signed,
                                     sandboxsafe=True,
                                     _nowrapper=True)
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
                        _nowrapper=True)
