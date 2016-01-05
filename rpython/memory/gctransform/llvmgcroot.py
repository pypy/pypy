"""
    This implements a StackRootWalker based on the data produced by the
    LLVM GC plug-in.
"""
from rpython.flowspace.model import Constant
from rpython.memory.gctransform.framework import (BaseFrameworkGCTransformer,
     BaseRootWalker)
from rpython.rlib.rarithmetic import r_uint, intmask, LONG_BIT
from rpython.rtyper import rmodel
from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.rbuiltin import gen_cast
from rpython.rtyper.rtyper import LowLevelOpList


# A "safe point" is the return address of a call.
# The "shape" of a safe point records the size of the frame of the function
# containing it, as well as a list of the variables that contain gc roots at
# that time.  Each variable is described by its offset in the frame.

SHAPE = lltype.Struct('Shape', ('framesize', lltype.Signed),
                               ('liveoffsets', lltype.Array(lltype.Signed)))
SHAPE_PTR = lltype.Ptr(SHAPE)
GCMAP = lltype.Array(('safe_point', llmemory.Address), ('shape', SHAPE_PTR))
HASHTABLE = lltype.Array(GCMAP.OF, hints={'nolength': True})
LIST_NODE = lltype.ForwardReference()
LIST_NODE_PTR = lltype.Ptr(LIST_NODE)
LIST_NODE.become(lltype.Struct('ListNode', ('next_', LIST_NODE_PTR),
                                           ('frame', llmemory.Address)))


class LLVMGcRootFrameworkGCTransformer(BaseFrameworkGCTransformer):
    def push_roots(self, hop, keep_current_args=False):
        return

    def pop_roots(self, hop, livevars):
        return

    def gct_direct_call(self, hop):
        fnptr = hop.spaceop.args[0].value
        try:
            close_stack = fnptr._obj._callable._gctransformer_hint_close_stack_
        except AttributeError:
            close_stack = False
        if close_stack:
            self.handle_call_with_close_stack(hop)
            livevars = self.push_roots(hop)
            self.default(hop)
            self.pop_roots(hop, livevars)
        else:
            BaseFrameworkGCTransformer.gct_direct_call(self, hop)

    def handle_call_with_close_stack(self, hop):
        fnptr = hop.spaceop.args[0].value
        graph = fnptr._obj.graph
        if graph in self._closed_stack:
            return
        self._closed_stack.add(graph)

        # push a new stack segment
        llops = LowLevelOpList()
        v_frameaddress = llops.genop('stack_current', [], llmemory.Address)
        v_top = llops.genop('getarrayitem',
                            [self.c_top_segment, Constant(0, lltype.Signed)],
                            LIST_NODE_PTR)
        v_new = llops.genop('llvm_stack_malloc', [], LIST_NODE_PTR)
        llops.genop('setfield', [v_new, Constant('next_', lltype.Void), v_top])
        llops.genop('setfield',
                    [v_new, Constant('frame', lltype.Void), v_frameaddress])
        llops.genop('setarrayitem',
                    [self.c_top_segment, Constant(0, lltype.Signed), v_new])
        graph.startblock.operations[:0] = llops

        # pop stack segment
        llops = LowLevelOpList()
        v_top = llops.genop('getarrayitem',
                            [self.c_top_segment, Constant(0, lltype.Signed)],
                            LIST_NODE_PTR)
        v_next = llops.genop('getfield',
                             [v_top, Constant('next_', lltype.Void)],
                             LIST_NODE_PTR)
        llops.genop('setarrayitem',
                    [self.c_top_segment, Constant(0, lltype.Signed), v_next])
        graph.startblock.operations.extend(llops)

    def build_root_walker(self):
        self._closed_stack = set()
        return LLVMStackRootWalker(self)


sizeofaddr = llmemory.sizeof(llmemory.Address)

class LLVMStackRootWalker(BaseRootWalker):
    def __init__(self, gctransformer):
        BaseRootWalker.__init__(self, gctransformer)
        self.top_segment = fs = lltype.malloc(
                lltype.FixedSizeArray(LIST_NODE_PTR, 1),
                immortal=True, zero=True)
        gctransformer.c_top_segment = Constant(fs, fs._TYPE)

    def setup_root_walker(self):
        hashtable_create(self.gcdata, llop.llvm_gcmap(lltype.Ptr(GCMAP)))

    def need_thread_support(self, gctransformer, getfn):
        pass

    def walk_stack_roots(self, collect_stack_root, is_minor=False):
        """Call `collect_stack_root()` for all gc roots on the stack.

        This is done by walking up the stack. For each safe point the hash
        table contains the stack frame's shape. The shape is a description of
        the offsets from the frame data base.
        """
        callee_bp = llop.stack_current(llmemory.Address)
        segment = llop.getarrayitem(LIST_NODE_PTR, self.top_segment, 0)
        while True:
            self._walk_stack_segment(collect_stack_root, callee_bp)
            if not segment:
                break
            callee_bp = segment.frame
            segment = segment.next_

    def _walk_stack_segment(self, collect_stack_root, callee_bp):
        while True:
            retaddr = callee_bp.address[1]
            caller_sp = callee_bp + 2 * sizeofaddr
            caller_shape = hashtable_get(self.gcdata, retaddr)

            i = 0
            while i < len(caller_shape.liveoffsets):
                root_loc = caller_sp + caller_shape.liveoffsets[i]
                if root_loc.address[0]:
                    collect_stack_root(self.gc, root_loc)
                i += 1

            if caller_shape.framesize & 1:
                return
            callee_bp += sizeofaddr + caller_shape.framesize


def hash_ptr(adr):
    intval = r_uint(llmemory.cast_adr_to_int(adr))
    return (intval >> 4) ^ (intval >> 9)

def hashtable_create(gcdata, gcmap):
    # length is number of entries * 1.5 rounded up to power of two
    mask = r_uint(len(gcmap) * 3 // 2) - 1
    i = 1
    while i < LONG_BIT:
        mask |= mask >> i
        i <<= 1
    gcdata.hash_table_mask = mask
    gcdata.hash_table = lltype.malloc(HASHTABLE, intmask(mask + 1),
                                      flavor='raw', zero=True)
    i = 0
    while i < len(gcmap):
        bucket = hash_ptr(gcmap[i].safe_point) & mask
        while gcdata.hash_table[bucket].safe_point:
            bucket = (bucket + 1) & mask
        gcdata.hash_table[bucket].safe_point = gcmap[i].safe_point
        gcdata.hash_table[bucket].shape = gcmap[i].shape
        i += 1

def hashtable_get(gcdata, retaddr):
    mask = gcdata.hash_table_mask
    bucket = hash_ptr(retaddr) & mask
    item = gcdata.hash_table[bucket]
    while item.safe_point != retaddr:
        if not item.safe_point:
            llop.debug_fatalerror(lltype.Void, "cannot find gc roots!")
        bucket = (bucket + 1) & mask
        item = gcdata.hash_table[bucket]
    return item.shape

def hashtable_free(gcdata):
    lltype.free(gcdata.hash_table, flavor='raw')
