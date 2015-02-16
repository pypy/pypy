
""" Bytecode for storage in asmmemmgr.jit_codemap. Format is as follows:

 list of tuples of shape (addr, machine code size, bytecode info)
 where bytecode info is a string made up of:
    8 bytes unique_id, 4 bytes start_addr (relative), 4 bytes size (relative),
    2 bytes how many items to skip to go to the next on similar level
    [so far represented by a list of integers for simplicity]

"""

from rpython.rlib import rgc
from rpython.rlib.entrypoint import jit_entrypoint
from rpython.jit.backend.llsupport import asmmemmgr
from rpython.rlib.rbisect import bisect_right, bisect_right_tuple
from rpython.rtyper.lltypesystem import lltype, rffi

@jit_entrypoint([lltype.Signed], lltype.Signed,
                c_name='pypy_jit_stack_depth_at_loc')
@rgc.no_collect
def stack_depth_at_loc(loc):
    _memmngr = asmmemmgr._memmngr

    pos = bisect_right(_memmngr.jit_addr_map, loc)
    if pos == 0 or pos == len(_memmngr.jit_addr_map):
        return -1
    return _memmngr.jit_frame_depth_map[pos - 1]

@jit_entrypoint([], lltype.Signed, c_name='pypy_jit_start_addr')
def jit_start_addr():
    _memmngr = asmmemmgr._memmngr

    return _memmngr.jit_addr_map[0]

@jit_entrypoint([], lltype.Signed, c_name='pypy_jit_end_addr')
def jit_end_addr():
    _memmngr = asmmemmgr._memmngr

    return _memmngr.jit_addr_map[-1]

@jit_entrypoint([lltype.Signed], lltype.Signed,
                c_name='pypy_find_codemap_at_addr')
def find_codemap_at_addr(addr):
    _memmngr = asmmemmgr._memmngr

    res = bisect_right_tuple(_memmngr.jit_codemap, addr) - 1
    return res

@jit_entrypoint([lltype.Signed, lltype.Signed,
                 rffi.CArrayPtr(lltype.Signed)], lltype.Signed,
                 c_name='pypy_yield_codemap_at_addr')
def yield_bytecode_at_addr(codemap_no, addr, current_pos_addr):
    """ will return consecutive unique_ids from codemap, starting from position
    `pos` until addr
    """
    _memmngr = asmmemmgr._memmngr

    codemap = _memmngr.jit_codemap[codemap_no]
    current_pos = current_pos_addr[0]
    start_addr = codemap[0]
    rel_addr = addr - start_addr
    while True:
        if current_pos >= len(codemap[2]):
            return 0
        next_start = codemap[2][current_pos + 1]
        if next_start > rel_addr:
            return 0
        next_stop = codemap[2][current_pos + 2]
        if next_stop > rel_addr:
            current_pos_addr[0] = current_pos + 4
            return codemap[2][current_pos]
        # we need to skip potentially more than one
        current_pos = codemap[2][current_pos + 3]

def unpack_traceback(addr):
    codemap_pos = find_codemap_at_addr(addr)
    if codemap_pos == -1:
        return [] # no codemap for that position
    storage = lltype.malloc(rffi.CArray(lltype.Signed), 1, flavor='raw')
    storage[0] = 0
    res = []
    while True:
        item = yield_bytecode_at_addr(codemap_pos, addr, storage)
        if item == 0:
            break
        res.append(item)
    lltype.free(storage, flavor='raw')
    return res


class CodemapBuilder(object):
    def __init__(self):
        self.l = []
        self.patch_position = []
        self.last_call_depth = -1

    def debug_merge_point(self, op, pos):
        call_depth = op.getarg(1).getint()
        if call_depth != self.last_call_depth:
            unique_id = op.getarg(3).getint()
            if unique_id == 0: # uninteresting case
                return
            assert unique_id & 1 == 0
            if call_depth > self.last_call_depth:
                self.l.append(unique_id)
                self.l.append(pos) # <- this is a relative pos
                self.patch_position.append(len(self.l))
                self.l.append(0) # marker
                self.l.append(0) # second marker
            else:
                for i in range(self.last_call_depth - call_depth):
                    to_patch = self.patch_position.pop()
                    self.l[to_patch] = pos
                    self.l[to_patch + 1] = len(self.l)
            self.last_call_depth = call_depth

    def inherit_code_from_position(self, pos):
        lst = unpack_traceback(pos)
        self.last_call_depth = len(lst) - 1
        for item in lst:
            self.l.append(item)
            self.l.append(0)
            self.patch_position.append(len(self.l))
            self.l.append(0) # marker
            self.l.append(0) # second marker

    def get_final_bytecode(self, addr, size):
        while self.patch_position:
            pos = self.patch_position.pop()
            self.l[pos] = size
            self.l[pos + 1] = len(self.l)
        # at the end there should be no zeros
        for i in range(len(self.l) / 4):
            item = self.l[i * 4] # unique_id
            assert item > 0 # no zeros here
            item = self.l[i * 4 + 2] # end in asm
            assert item > 0
            item = self.l[i * 4 + 3] # end in l
            assert item > 0
        return (addr, size, self.l) # XXX compact self.l

