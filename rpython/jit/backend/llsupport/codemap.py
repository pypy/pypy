
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


eci = ExternalCompilationInfo(post_include_bits=["""
RPY_EXTERN long pypy_jit_codemap_add(uintptr_t addr,
                                     unsigned int machine_code_size,
                                     long *bytecode_info,
                                     unsigned int bytecode_info_size);
RPY_EXTERN void pypy_jit_codemap_del(uintptr_t addr);

RPY_EXTERN long pypy_jit_depthmap_add(uintptr_t addr, unsigned int size,
                                      unsigned int stackdepth);
RPY_EXTERN void pypy_jit_depthmap_clear(uintptr_t addr, unsigned int size);

"""], separate_module_files=[
    os.path.join(os.path.dirname(__file__), 'src', 'codemap.c')
])

def llexternal(name, args, res):
    return rffi.llexternal(name, args, res, compilation_info=eci,
                           releasegil=False)

ll_pypy_codemap_invalid_set = llexternal('pypy_codemap_invalid_set',
                                         [rffi.INT], lltype.Void)
pypy_get_codemap_storage = llexternal('pypy_get_codemap_storage',
                                      [], lltype.Ptr(CODEMAP_STORAGE))
stack_depth_at_loc = llexternal('pypy_jit_stack_depth_at_loc',
                                [lltype.Signed], lltype.Signed)
find_codemap_at_addr = llexternal('pypy_find_codemap_at_addr',
                                  [lltype.Signed], lltype.Signed)
yield_bytecode_at_addr = llexternal('pypy_yield_codemap_at_addr',
                                    [lltype.Signed, lltype.Signed,
                                     rffi.CArrayPtr(lltype.Signed)],
                                     lltype.Signed)

def pypy_codemap_invalid_set(val):
    #if we_are_translated():
    ll_pypy_codemap_invalid_set(val)

@specialize.ll()
def copy_item(source, dest, si, di, baseline=0):
    TP = lltype.typeOf(dest)
    if isinstance(TP.TO.OF, lltype.Struct):
        rgc.copy_struct_item(source, dest, si, di)
    else:
        dest[di] = source[si] + baseline

class ListStorageMixin(object):
    _mixin_ = True

    @specialize.arg(1)
    def extend_with(self, name, to_insert, pos, baseline=0):
        xxxx
        # first check if we need to reallocate
        g = pypy_get_codemap_storage()
        used = getattr(g, name + '_used')
        allocated = getattr(self, name + '_allocated')
        lst = getattr(g, name)
        if used + len(to_insert) > allocated or pos != used:
            old_lst = lst
            if used + len(to_insert) > allocated:
                new_size = max(4 * allocated,
                               (allocated + len(to_insert)) * 2)
            else:
                new_size = allocated
            lst = lltype.malloc(lltype.typeOf(lst).TO, new_size,
                                flavor='raw',
                                track_allocation=False)
            setattr(self, name + '_allocated', new_size)
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
        setattr(g, name, lst)
        setattr(g, name + '_used', len(to_insert) + used)

    @specialize.arg(1)
    def remove(self, name, start, end):
        g = pypy_get_codemap_storage()
        lst = getattr(g, name)
        used = getattr(g, name + '_used')
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
        setattr(g, name + '_used', used - (end - start))

    def free(self):
        g = pypy_get_codemap_storage()
        # if setup has not been called
        if g.jit_addr_map_used:
            lltype.free(g.jit_addr_map, flavor='raw', track_allocation=False)
            g.jit_addr_map_used = 0
            g.jit_addr_map = lltype.nullptr(INT_LIST)
        i = 0
        while i < g.jit_codemap_used:
            lltype.free(g.jit_codemap[i].bytecode_info, flavor='raw',
                        track_allocation=False)
            i += 1
        if g.jit_codemap_used:
            lltype.free(g.jit_codemap, flavor='raw',
                        track_allocation=False)
            g.jit_codemap_used = 0
            g.jit_codemap = lltype.nullptr(CODEMAP_LIST)
        if g.jit_frame_depth_map_used:
            lltype.free(g.jit_frame_depth_map, flavor='raw',
                        track_allocation=False)
            g.jit_frame_depth_map_used = 0
            g.jit_frame_depth_map = lltype.nullptr(INT_LIST)

    @specialize.arg(1)
    def free_lst(self, name, lst):
        if lst:
            lltype.free(lst, flavor='raw', track_allocation=False)

class CodemapStorage(ListStorageMixin):
    """ An immortal wrapper around underlaying jit codemap data
    """
    def setup(self):
        g = pypy_get_codemap_storage()
        if g.jit_addr_map_used != 0:
             # someone failed to call free(), in tests only anyway
             self.free()

    def free_asm_block(self, start, stop):
        # fix up jit_addr_map
        g = pypy_get_codemap_storage()
        jit_adr_start = bisect_left(g.jit_addr_map, start,
                                    g.jit_addr_map_used)
        jit_adr_stop = bisect_left(g.jit_addr_map, stop,
                                   g.jit_addr_map_used)
        pypy_codemap_invalid_set(1)
        self.remove('jit_addr_map', jit_adr_start, jit_adr_stop)
        self.remove('jit_frame_depth_map', jit_adr_start, jit_adr_stop)
        # fix up codemap
        # (there should only be zero or one codemap entry in that range,
        # but still we use a range to distinguish between zero and one)
        codemap_adr_start = bisect_left_addr(g.jit_codemap, start,
                                             g.jit_codemap_used)
        codemap_adr_stop = bisect_left_addr(g.jit_codemap, stop,
                                            g.jit_codemap_used)
        self.remove('jit_codemap', codemap_adr_start, codemap_adr_stop)
        pypy_codemap_invalid_set(0)

    def register_frame_depth_map(self, rawstart, frame_positions,
                                 frame_assignments):
        if not frame_positions:
            return
        pypy_codemap_invalid_set(1)
        g = pypy_get_codemap_storage()
        if (not g.jit_addr_map_used or
            rawstart > g.jit_addr_map[g.jit_addr_map_used - 1]):
            start = g.jit_addr_map_used
            self.extend_with('jit_addr_map', frame_positions,
                             g.jit_addr_map_used, rawstart)
            self.extend_with('jit_frame_depth_map', frame_assignments,
                             g.jit_frame_depth_map_used)
        else:
            start = bisect_left(g.jit_addr_map, rawstart,
                                g.jit_addr_map_used)
            self.extend_with('jit_addr_map', frame_positions, start, rawstart)
            self.extend_with('jit_frame_depth_map', frame_assignments,
                             start)
        pypy_codemap_invalid_set(0)

    def register_codemap(self, (start, size, l)):
        items = lltype.malloc(INT_LIST, len(l), flavor='raw',
                              track_allocation=False)
        for i in range(len(l)):
            items[i] = l[i]
        if pypy_jit_codemap_add(start, size, items, len(l)) < 0:
            lltype.free(items, flavor='raw', track_allocation=False)

    def finish_once(self):
        self.free()

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
