from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.annlowlevel import llhelper


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

def search_in_gcmap_direct(gcmapstart, gcmapend, key):
    # same as 'search_in_gcmap' in asmgcroot.py, but without range checking
    # support (item.address[1] is an address in this case, not a int at all!)
    item = binary_search(gcmapstart, gcmapend, key)
    if item.address[0] == key:
        return item.address[1]     # found
    else:
        return llmemory.NULL    # failed

def sort_gcmap(gcmapstart, gcmapend):
    count = (gcmapend - gcmapstart) // arrayitemsize
    qsort(gcmapstart,
          rffi.cast(rffi.SIZE_T, count),
          rffi.cast(rffi.SIZE_T, arrayitemsize),
          llhelper(QSORT_CALLBACK_PTR, _compare_gcmap_entries))

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

def replace_dead_entries_with_nulls(start, end):
    # replace the dead entries (null value) with a null key.
    count = (end - start) // arrayitemsize - 1
    while count >= 0:
        item = start + count * arrayitemsize
        if item.address[1] == llmemory.NULL:
            item.address[0] = llmemory.NULL
        count -= 1

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


class GcJitTableSearch(object):

    def __init__(self, translator):
        if hasattr(translator, '_jit2gc'):
            jit2gc = translator._jit2gc
            self._extra_gcmapstart  = jit2gc['gcmapstart']
            self._extra_gcmapend    = jit2gc['gcmapend']
            self._extra_mark_sorted = jit2gc['gcmarksorted']
        else:
            self._extra_gcmapstart  = lambda: llmemory.NULL
            self._extra_gcmapend    = lambda: llmemory.NULL
            self._extra_mark_sorted = lambda: True

    def _freeze_(self):
        return True

    def look_in_jit_table(self, key):
        gcmapstart2 = self._extra_gcmapstart()
        gcmapend2   = self._extra_gcmapend()
        if gcmapstart2 == gcmapend2:
            return llmemory.NULL
        # we have a non-empty JIT-produced table to look in
        item = search_in_gcmap_direct(gcmapstart2, gcmapend2, key)
        if item:
            return item
        # maybe the JIT-produced table is not sorted?
        was_already_sorted = self._extra_mark_sorted()
        if not was_already_sorted:
            sort_gcmap(gcmapstart2, gcmapend2)
            item = search_in_gcmap_direct(gcmapstart2, gcmapend2, key)
            if item:
                return item
        # there is a rare risk that the array contains *two* entries
        # with the same key, one of which is dead (null value), and we
        # found the dead one above.  Solve this case by replacing all
        # dead keys with nulls, sorting again, and then trying again.
        replace_dead_entries_with_nulls(gcmapstart2, gcmapend2)
        sort_gcmap(gcmapstart2, gcmapend2)
        item = search_in_gcmap_direct(gcmapstart2, gcmapend2, key)
        return item
