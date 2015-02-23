
""" Bytecode for storage in asmmemmgr.jit_codemap. Format is as follows:

 list of tuples of shape (addr, machine code size, bytecode info)
 where bytecode info is a string made up of:
    8 bytes unique_id, 4 bytes start_addr (relative), 4 bytes size (relative),
    2 bytes how many items to skip to go to the next on similar level
    [so far represented by a list of integers for simplicity]

"""

from rpython.rlib import rgc
from rpython.rlib.objectmodel import specialize, we_are_translated
from rpython.rlib.entrypoint import jit_entrypoint
from rpython.rlib.rbisect import bisect_right, bisect_right_addr
from rpython.rlib.rbisect import bisect_left, bisect_left_addr
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo

INITIAL_SIZE = 1000
GROWTH_FACTOR = 4

INT_LIST = lltype.Array(lltype.Signed) # raw, but with length

CODEMAP = lltype.Struct(
    'codemap',
    ('addr', lltype.Signed),
    ('machine_code_size', lltype.Signed),
    ('bytecode_info', lltype.Ptr(INT_LIST)))
CODEMAP_LIST = lltype.Array(CODEMAP)

CODEMAP_GCARRAY = lltype.GcArray(CODEMAP)

_codemap = None

eci = ExternalCompilationInfo(post_include_bits=["""
RPY_EXTERN volatile int pypy_codemap_currently_invalid;
RPY_EXTERN void pypy_codemap_invalid_set(int);
"""], separate_module_sources=["""
volatile int pypy_codemap_currently_invalid = 0;

void pypy_codemap_invalid_set(int value)
{
    pypy_codemap_currently_invalid = value;
}
"""])

ll_pypy_codemap_invalid_set = rffi.llexternal('pypy_codemap_invalid_set',
                                              [rffi.INT], lltype.Void,
                                              compilation_info=eci,
                                              releasegil=False)

def pypy_codemap_invalid_set(val):
    if we_are_translated():
        ll_pypy_codemap_invalid_set(val)

@specialize.ll()
def copy_item(source, dest, si, di, baseline=0):
    TP = lltype.typeOf(dest)
    if isinstance(TP.TO.OF, lltype.Struct):
        rgc.copy_struct_item(source, dest, si, di)
    else:
        dest[di] = source[si] + baseline

class ListStorageMixin(object):
    # XXX this code has wrong complexity, we should come up with a better
    #     data structure ideally
    _mixin_ = True

    @specialize.arg(1)
    def extend_with(self, name, to_insert, pos, baseline=0):
        # first check if we need to reallocate
        used = getattr(self, name + '_used')
        allocated = len(getattr(self, name))
        lst = getattr(self, name)
        if pos + len(to_insert) >= allocated or pos != used:
            old_lst = lst
            if pos == used:
                new_size = max(4 * len(old_lst),
                               (len(old_lst) + len(to_insert)) * 2)
                lst = lltype.malloc(lltype.typeOf(lst).TO, new_size,
                                    flavor='raw',
                                    track_allocation=self.track_allocation)
            else:
                lst = lltype.malloc(lltype.typeOf(lst).TO, len(old_lst),
                                    flavor='raw',
                                    track_allocation=self.track_allocation)
            for i in range(0, pos):
                copy_item(old_lst, lst, i, i)
            j = 0
            for i in range(pos, pos + len(to_insert)):
                copy_item(to_insert, lst, j, i, baseline)
                j += 1
            j = pos
            for i in range(pos + len(to_insert), len(to_insert) + used):
                copy_item(old_lst, lst, j, i)
                j += 1
            self.free_lst(name, old_lst)
        else:
            for i in range(len(to_insert)):
                copy_item(to_insert, lst, i, i + pos, baseline)
        pypy_codemap_invalid_set(1)
        setattr(self, name, lst)
        setattr(self, name + '_used', len(to_insert) + used)
        pypy_codemap_invalid_set(0)

    @specialize.arg(1)
    def remove(self, name, start, end):
        pypy_codemap_invalid_set(1)
        lst = getattr(self, name)
        used = getattr(self, name + '_used')
        j = end
        for i in range(start, used - (end - start)):
            info = lltype.nullptr(INT_LIST)
            if name == 'jit_codemap':
                if i < end:
                    info = lst[i].bytecode_info
            copy_item(lst, lst, j, i)
            if name == 'jit_codemap':
                if info:
                    lltype.free(info, flavor='raw', track_allocation=False)
            j += 1
        setattr(self, name + '_used', used - (end - start))
        pypy_codemap_invalid_set(0)

class CodemapStorage(ListStorageMixin):
    """ An immortal wrapper around underlaying jit codemap data
    """
    track_allocation = False
    jit_addr_map = lltype.nullptr(INT_LIST)
    jit_addr_map_used = 0
    jit_codemap = lltype.nullptr(CODEMAP_LIST)
    jit_codemap_used = 0
    jit_frame_depth_map = lltype.nullptr(INT_LIST)
    jit_frame_depth_map_used = 0
    
    def __init__(self):
        global _codemap

        _codemap = self # a global singleton, for @entrypoint, self it's
        # a prebuilt constant anyway

    def setup(self):
        self.jit_addr_map = lltype.malloc(INT_LIST, INITIAL_SIZE, flavor='raw',
                                          track_allocation=False)
        self.jit_addr_map_used = 0
        self.jit_codemap = lltype.malloc(CODEMAP_LIST, INITIAL_SIZE,
                                         flavor='raw',
                                         track_allocation=False)
        self.jit_codemap_used = 0
        self.jit_frame_depth_map = lltype.malloc(INT_LIST, INITIAL_SIZE,
                                                 flavor='raw',
                                                 track_allocation=False)
        self.jit_frame_depth_map_used = 0

    @specialize.arg(1)
    def free_lst(self, name, lst):
        lltype.free(lst, flavor='raw', track_allocation=False)

    def __del__(self):
        self.free()

    def free(self):
        # if setup has not been called
        if not self.jit_addr_map:
            return
        lltype.free(self.jit_addr_map, flavor='raw')
        i = 0
        while i < self.jit_codemap_used:
            lltype.free(self.jit_codemap[i].bytecode_info, flavor='raw')
            i += 1
        lltype.free(self.jit_codemap, flavor='raw')
        lltype.free(self.jit_frame_depth_map, flavor='raw')
        self.jit_adr_map = lltype.nullptr(INT_LIST)

    def free_asm_block(self, start, stop):
        # fix up jit_addr_map
        jit_adr_start = bisect_left(self.jit_addr_map, start,
                                    self.jit_addr_map_used)
        jit_adr_stop = bisect_left(self.jit_addr_map, stop,
                                   self.jit_addr_map_used)
        self.remove('jit_addr_map', jit_adr_start, jit_adr_stop)
        self.remove('jit_frame_depth_map', jit_adr_start, jit_adr_stop)
        # fix up codemap
        # (there should only be zero or one codemap entry in that range,
        # but still we use a range to distinguish between zero and one)
        codemap_adr_start = bisect_left_addr(self.jit_codemap, start,
                                             self.jit_codemap_used)
        codemap_adr_stop = bisect_left_addr(self.jit_codemap, stop,
                                            self.jit_codemap_used)
        self.remove('jit_codemap', codemap_adr_start, codemap_adr_stop)

    def register_frame_depth_map(self, rawstart, frame_positions,
                                 frame_assignments):
        if not frame_positions:
            return
        if (not self.jit_addr_map_used or
            rawstart > self.jit_addr_map[self.jit_addr_map_used - 1]):
            start = self.jit_addr_map_used
            self.extend_with('jit_addr_map', frame_positions,
                             self.jit_addr_map_used, rawstart)
            self.extend_with('jit_frame_depth_map', frame_assignments,
                             self.jit_frame_depth_map_used)
        else:
            start = bisect_left(self.jit_addr_map, rawstart,
                                self.jit_addr_map_used)
            self.extend_with('jit_addr_map', frame_positions, start, rawstart)
            self.extend_with('jit_frame_depth_map', frame_assignments,
                             start)

    def register_codemap(self, codemap):
        start = codemap[0]
        pos = bisect_left_addr(self.jit_codemap, start, self.jit_codemap_used)
        items = lltype.malloc(INT_LIST, len(codemap[2]), flavor='raw',
                             track_allocation=False)
        for i in range(len(codemap[2])):
            items[i] = codemap[2][i]
        s = lltype.malloc(CODEMAP_GCARRAY, 1)
        s[0].addr = codemap[0]
        s[0].machine_code_size = codemap[1]
        s[0].bytecode_info = items
        self.extend_with('jit_codemap', s, pos)

@jit_entrypoint([lltype.Signed], lltype.Signed,
                c_name='pypy_jit_stack_depth_at_loc')
@rgc.no_collect
def stack_depth_at_loc(loc):
    global _codemap

    pos = bisect_right(_codemap.jit_addr_map, loc, _codemap.jit_addr_map_used)
    if pos == 0 or pos == _codemap.jit_addr_map_used:
        return -1
    return _codemap.jit_frame_depth_map[pos - 1]

@jit_entrypoint([], lltype.Signed, c_name='pypy_jit_start_addr')
def jit_start_addr():
    global _codemap

    return _codemap.jit_addr_map[0]

@jit_entrypoint([], lltype.Signed, c_name='pypy_jit_end_addr')
def jit_end_addr():
    global _codemap

    return _codemap.jit_addr_map[_codemap.jit_addr_map_used - 1]

@jit_entrypoint([lltype.Signed], lltype.Signed,
                c_name='pypy_find_codemap_at_addr')
def find_codemap_at_addr(addr):
    global _codemap

    res = bisect_right_addr(_codemap.jit_codemap, addr,
                            _codemap.jit_codemap_used) - 1
    return res

@jit_entrypoint([lltype.Signed, lltype.Signed,
                 rffi.CArrayPtr(lltype.Signed)], lltype.Signed,
                 c_name='pypy_yield_codemap_at_addr')
def yield_bytecode_at_addr(codemap_no, addr, current_pos_addr):
    """ will return consecutive unique_ids from codemap, starting from position
    `pos` until addr
    """
    global _codemap

    codemap = _codemap.jit_codemap[codemap_no]
    current_pos = current_pos_addr[0]
    start_addr = codemap.addr
    rel_addr = addr - start_addr
    while True:
        if current_pos >= len(codemap.bytecode_info):
            return 0
        next_start = codemap.bytecode_info[current_pos + 1]
        if next_start > rel_addr:
            return 0
        next_stop = codemap.bytecode_info[current_pos + 2]
        if next_stop > rel_addr:
            current_pos_addr[0] = current_pos + 4
            return codemap.bytecode_info[current_pos]
        # we need to skip potentially more than one
        current_pos = codemap.bytecode_info[current_pos + 3]

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

    def debug_merge_point(self, call_depth, unique_id, pos):
        if call_depth != self.last_call_depth:
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

