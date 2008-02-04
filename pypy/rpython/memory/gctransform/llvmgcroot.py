from pypy.rpython.memory.gctransform.framework import FrameworkGCTransformer
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.lltypesystem.lloperation import llop
from pypy.rpython import rmodel
from pypy.rpython.rbuiltin import gen_cast
from pypy.rlib.debug import ll_assert


#
#  This implements a StackRootWalker based on the data produced by
#  the llvm GC plug-in found over there:
#
#     http://codespeak.net/svn/user/arigo/hack/pypy-hack/stackrootwalker
#


class LLVMGcRootFrameworkGCTransformer(FrameworkGCTransformer):
    # XXX this is completely specific to the llvm backend at the moment.

    def push_roots(self, hop, keep_current_args=False):
        livevars = self.get_livevars_for_roots(hop, keep_current_args)
        self.num_pushs += len(livevars)
        if not livevars:
            return []
        for k, var in enumerate(livevars):
            c_k = rmodel.inputconst(lltype.Signed, k)
            v_adr = gen_cast(hop.llops, llmemory.Address, var)
            hop.genop("llvm_store_gcroot", [c_k, v_adr])
        return livevars

    def pop_roots(self, hop, livevars):
        if not livevars:
            return
        if self.gcdata.gc.moving_gc:
            # for moving collectors, reload the roots into the local variables
            for k, var in enumerate(livevars):
                c_k = rmodel.inputconst(lltype.Signed, k)
                v_newaddr = hop.genop("llvm_load_gcroot", [c_k],
                                      resulttype=llmemory.Address)
                hop.genop("gc_reload_possibly_moved", [v_newaddr, var])
        # XXX for now, the values stay in the gcroots.  It might keep
        # some old objects alive for a bit longer than necessary.

    def build_stack_root_iterator(self):
        gcdata = self.gcdata

        class StackRootIterator:
            _alloc_flavor_ = 'raw'

            def setup_root_stack():
                # The gcmap table is a list of pairs of pointers:
                #     void *SafePointAddress;
                #     void *Shape;
                # Here, i.e. when the program starts, we sort it
                # in-place on the SafePointAddress to allow for more
                # efficient searches.
                gcmapstart = llop.llvm_gcmapstart(llmemory.Address)
                gcmapend   = llop.llvm_gcmapend(llmemory.Address)
                insertion_sort(gcmapstart, gcmapend)
            setup_root_stack = staticmethod(setup_root_stack)

            need_root_stack = False

            def append_static_root(adr):
                gcdata.static_root_end.address[0] = adr
                gcdata.static_root_end += sizeofaddr
            append_static_root = staticmethod(append_static_root)
            
            def __init__(self, with_static=True):
                self.stack_current = llop.llvm_frameaddress(llmemory.Address)
                self.remaining_roots_in_current_frame = 0
                # We must walk at least a couple of frames up the stack
                # *now*, i.e. before we leave __init__, otherwise
                # self.stack_current ends up pointing to a dead frame.
                # We can walk until we find a real GC root; then we're
                # definitely out of the GC code itself.
                while self.remaining_roots_in_current_frame == 0:
                    if not self.walk_to_parent_frame():
                        break     # not a single GC root? unlikely but not
                                  # impossible I guess
                if with_static:
                    self.static_current = gcdata.static_root_end
                else:
                    self.static_current = gcdata.static_root_nongcend

            def pop(self):
                while self.static_current != gcdata.static_root_start:
                    self.static_current -= sizeofaddr
                    result = self.static_current.address[0]
                    if result.address[0] != llmemory.NULL:
                        return result

                while True:
                    while self.remaining_roots_in_current_frame == 0:
                        if not self.walk_to_parent_frame():
                            return llmemory.NULL
                    result = self.next_gcroot_from_current_frame()
                    if result.address[0] != llmemory.NULL:
                        return result

            def walk_to_parent_frame(self):
                #
                # The gcmap table is a list of pairs of pointers:
                #     void *SafePointAddress;
                #     void *Shape;
                #
                # A "safe point" is the return address of a call.
                # The "shape" of a safe point records the size of the
                # frame of the function containing it, as well as a
                # list of the variables that contain gc roots at that
                # time.  Each variable is described by its offset in
                # the frame.
                #
                callee_frame = self.stack_current
                if llmemory.cast_adr_to_int(callee_frame) & 1:
                    return False   # odd bit set here when the callee_frame
                                   # is the frame of main(), i.e. when there
                                   # is nothing more for us in the stack.
                #
                # XXX the details are completely specific to X86!!!
                # a picture of the stack may help:
                #                                           ^ ^ ^
                #     |     ...      |                 to older frames
                #     +--------------+
                #     |  first word  |  <------ caller_frame (addr of 1st word)
                #     +              +
                #     | caller frame |
                #     |     ...      |
                #     |  frame data  |  <------ frame_data_base
                #     +--------------+
                #     |   ret addr   |
                #     +--------------+
                #     |  first word  |  <------ callee_frame (addr of 1st word)
                #     +              +
                #     | callee frame |
                #     |     ...      |
                #     |  frame data  |                 lower addresses
                #     +--------------+                      v v v
                #
                retaddr = callee_frame.address[1]
                #
                # try to locate the caller function based on retaddr.
                #
                gcmapstart = llop.llvm_gcmapstart(llmemory.Address)
                gcmapend   = llop.llvm_gcmapend(llmemory.Address)
                item = binary_search(gcmapstart, gcmapend, retaddr)
                if item.address[0] == retaddr:
                    #
                    # found!  Setup pointers allowing us to
                    # parse the caller's frame structure...
                    #
                    shape = item.address[1]
                    # XXX assumes that .signed is 32-bit
                    framesize = shape.signed[0]   # odd if it's main()
                    livecount = shape.signed[1]
                    caller_frame = callee_frame + 4 + framesize
                    self.stack_current = caller_frame
                    self.frame_data_base = callee_frame + 8
                    self.remaining_roots_in_current_frame = livecount
                    self.liveoffsets = shape + 8
                    return True

                # retaddr not found!
                llop.debug_fatalerror(lltype.Void, "cannot find gc roots!")
                return False

            def next_gcroot_from_current_frame(self):
                i = self.remaining_roots_in_current_frame - 1
                self.remaining_roots_in_current_frame = i
                ll_assert(i >= 0, "bad call to next_gcroot_from_current_frame")
                liveoffset = self.liveoffsets.signed[i]
                return self.frame_data_base + liveoffset


        return StackRootIterator


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

def insertion_sort(start, end):
    """Sort an array of pairs of addresses.

    This is an insertion sort, so it's slowish unless the array is mostly
    sorted already (which is what I expect, but XXX check this).
    """
    next = start
    while next < end:
        # assuming the interval from start (included) to next (excluded)
        # to be already sorted, move the next element back into the array
        # until it reaches its proper place.
        addr1 = next.address[0]
        addr2 = next.address[1]
        scan = next
        while scan > start and addr1 < scan.address[-2]:
            scan.address[0] = scan.address[-2]
            scan.address[1] = scan.address[-1]
            scan -= arrayitemsize
        scan.address[0] = addr1
        scan.address[1] = addr2
        next += arrayitemsize
