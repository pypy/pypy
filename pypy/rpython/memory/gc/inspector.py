"""
Utility RPython functions to inspect objects in the GC.
"""
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rlib.objectmodel import free_non_gc_object
from pypy.rpython.module.ll_os import underscore_on_windows
from pypy.rlib import rposix

from pypy.rpython.memory.support import AddressDict, get_address_stack


# ---------- implementation of pypy.rlib.rgc.get_rpy_roots() ----------

def _counting_rpy_root(gc, root):
    gc._count_rpy += 1

def _do_count_rpy_roots(gc):
    gc._count_rpy = 0
    gc.root_walker.walk_roots(
        _counting_rpy_root,
        _counting_rpy_root,
        _counting_rpy_root)
    return gc._count_rpy

def _append_rpy_root(gc, root):
    # Can use the gc list, but should not allocate!
    # It is essential that the list is not resizable!
    lst = gc._list_rpy
    index = gc._count_rpy
    if index >= len(lst):
        raise ValueError
    gc._count_rpy = index + 1
    lst[index] = llmemory.cast_adr_to_ptr(root.address[0], llmemory.GCREF)

def _do_append_rpy_roots(gc, lst):
    gc._count_rpy = 0
    gc._list_rpy = lst
    gc.root_walker.walk_roots(
        _append_rpy_root,
        _append_rpy_root,
        _append_rpy_root)
    gc._list_rpy = None

def get_rpy_roots(gc):
    count = _do_count_rpy_roots(gc)
    extra = 16
    while True:
        result = [lltype.nullptr(llmemory.GCREF.TO)] * (count + extra)
        try:
            _do_append_rpy_roots(gc, result)
        except ValueError:
            extra *= 3
        else:
            return result

# ---------- implementation of pypy.rlib.rgc.get_rpy_referents() ----------

def _count_rpy_referent(pointer, gc):
    gc._count_rpy += 1

def _do_count_rpy_referents(gc, gcref):
    gc._count_rpy = 0
    gc.trace(llmemory.cast_ptr_to_adr(gcref), _count_rpy_referent, gc)
    return gc._count_rpy

def _append_rpy_referent(pointer, gc):
    # Can use the gc list, but should not allocate!
    # It is essential that the list is not resizable!
    lst = gc._list_rpy
    index = gc._count_rpy
    if index >= len(lst):
        raise ValueError
    gc._count_rpy = index + 1
    lst[index] = llmemory.cast_adr_to_ptr(pointer.address[0],
                                          llmemory.GCREF)

def _do_append_rpy_referents(gc, gcref, lst):
    gc._count_rpy = 0
    gc._list_rpy = lst
    gc.trace(llmemory.cast_ptr_to_adr(gcref), _append_rpy_referent, gc)

def get_rpy_referents(gc, gcref):
    count = _do_count_rpy_referents(gc, gcref)
    result = [lltype.nullptr(llmemory.GCREF.TO)] * count
    _do_append_rpy_referents(gc, gcref, result)
    return result

# ----------

def get_rpy_memory_usage(gc, gcref):
    return gc.get_size_incl_hash(llmemory.cast_ptr_to_adr(gcref))

def get_rpy_type_index(gc, gcref):
    typeid = gc.get_type_id(llmemory.cast_ptr_to_adr(gcref))
    return gc.get_member_index(typeid)

def is_rpy_instance(gc, gcref):
    typeid = gc.get_type_id(llmemory.cast_ptr_to_adr(gcref))
    return gc.is_rpython_class(typeid)

# ----------

raw_os_write = rffi.llexternal(underscore_on_windows+'write',
                               [rffi.INT, rffi.CArrayPtr(lltype.Signed),
                                rffi.SIZE_T],
                               rffi.SIZE_T,
                               sandboxsafe=True, _nowrapper=True)

AddressStack = get_address_stack()

class HeapDumper:
    _alloc_flavor_ = "raw"
    BUFSIZE = 8192     # words

    def __init__(self, gc, fd):
        self.gc = gc
        self.fd = rffi.cast(rffi.INT, fd)
        self.writebuffer = lltype.malloc(rffi.LONGP.TO, self.BUFSIZE,
                                         flavor='raw')
        self.buf_count = 0
        self.seen = AddressDict()
        self.pending = AddressStack()

    def delete(self):
        self.seen.delete()
        self.pending.delete()
        lltype.free(self.writebuffer, flavor='raw')
        free_non_gc_object(self)

    def flush(self):
        if self.buf_count > 0:
            bytes = self.buf_count * rffi.sizeof(rffi.LONG)
            count = raw_os_write(self.fd,
                                 self.writebuffer,
                                 rffi.cast(rffi.SIZE_T, bytes))
            if rffi.cast(lltype.Signed, count) != bytes:
                raise OSError(rposix.get_errno(), "raw_os_write failed")
            self.buf_count = 0
    flush._dont_inline_ = True

    def write(self, value):
        x = self.buf_count
        self.writebuffer[x] = llmemory.raw_malloc_usage(value)
        x += 1
        self.buf_count = x
        if x == self.BUFSIZE:
            self.flush()
    write._always_inline_ = True

    def write_marker(self):
        self.write(0)
        self.write(0)
        self.write(0)
        self.write(-1)

    def writeobj(self, obj):
        gc = self.gc
        typeid = gc.get_type_id(obj)
        self.write(llmemory.cast_adr_to_int(obj))
        self.write(gc.get_member_index(typeid))
        self.write(gc.get_size_incl_hash(obj))
        gc.trace(obj, self._writeref, None)
        self.write(-1)

    def _writeref(self, pointer, _):
        obj = pointer.address[0]
        self.write(llmemory.cast_adr_to_int(obj))
        self.add(obj)

    def add(self, obj):
        if not self.seen.contains(obj):
            self.seen.setitem(obj, obj)
            self.pending.append(obj)

    def add_roots(self):
        self.gc._heap_dumper = self
        self.gc.root_walker.walk_roots(
            _hd_add_root,
            _hd_add_root,
            _hd_add_root)
        self.gc._heap_dumper = None
        pendingroots = self.pending
        self.pending = AddressStack()
        self.walk(pendingroots)
        pendingroots.delete()
        self.write_marker()

    def walk(self, pending):
        while pending.non_empty():
            self.writeobj(pending.pop())

def _hd_add_root(gc, root):
    gc._heap_dumper.add(root.address[0])

def dump_rpy_heap(gc, fd):
    heapdumper = HeapDumper(gc, fd)
    heapdumper.add_roots()
    heapdumper.walk(heapdumper.pending)
    heapdumper.flush()
    heapdumper.delete()
    return True
