from pypy.rpython.memory.lladdress import raw_malloc, raw_free, raw_memcopy
from pypy.rpython.memory.lladdress import NULL, address
from pypy.rpython.memory.support import get_address_linked_list
from pypy.rpython.memory import lltypesimulation
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.objectmodel import free_non_gc_object
from pypy.rpython import rarithmetic

import sys

int_size = lltypesimulation.sizeof(lltype.Signed)

class GCHeaderOffset(llmemory.AddressOffset):
    def __init__(self, minimal_size):
        self.minimal_size = minimal_size
    def __int__(self):
        from pypy.rpython.memory.lltypelayout import sizeof
        return sizeof(self.minimal_size)
    # XXX blech
    def __radd__(self, other):
        return int(self) + other

gc_header_two_ints = GCHeaderOffset(
    lltype.Struct("header", ("a", lltype.Signed), ("b", lltype.Signed)))

gc_header_one_int = GCHeaderOffset(
    lltype.Struct("header", ("a", lltype.Signed)))

class GCError(Exception):
    pass

def get_dummy_annotate(gc_class, AddressLinkedList):
    def dummy_annotate():
        gc = gc_class(AddressLinkedList)
        gc.setup()
        gc.get_roots = dummy_get_roots1 #prevent the get_roots attribute to 
        gc.get_roots = dummy_get_roots2 #be constants
        a = gc.malloc(1, 2)
        b = gc.malloc(2, 3)
        gc.write_barrier(raw_malloc(1), raw_malloc(2), raw_malloc(1))
        gc.collect()
        return a - b

    def dummy_get_roots1():
        ll = AddressLinkedList()
        ll.append(NULL)
        ll.append(raw_malloc(10))
        ll.pop() #make the annotator see pop
        return ll

    def dummy_get_roots2():
        ll = AddressLinkedList()
        ll.append(raw_malloc(10))
        ll.append(NULL)
        ll.pop() #make the annotator see pop
        return ll
    return dummy_annotate, dummy_get_roots1, dummy_get_roots2


gc_interface = {
    "malloc": lltype.FuncType((lltype.Signed, lltype.Signed), lltype.Signed),
    "collect": lltype.FuncType((), lltype.Void),
    "write_barrier": lltype.FuncType((llmemory.Address, ) * 3, lltype.Void),
    }
    

class GCBase(object):
    _alloc_flavor_ = "raw"

    def set_query_functions(self, is_varsize, offsets_to_gc_pointers,
                            fixed_size, varsize_item_sizes,
                            varsize_offset_to_variable_part,
                            varsize_offset_to_length,
                            varsize_offsets_to_gcpointers_in_var_part):
        self.is_varsize = is_varsize
        self.offsets_to_gc_pointers = offsets_to_gc_pointers
        self.fixed_size = fixed_size
        self.varsize_item_sizes = varsize_item_sizes
        self.varsize_offset_to_variable_part = varsize_offset_to_variable_part
        self.varsize_offset_to_length = varsize_offset_to_length
        self.varsize_offsets_to_gcpointers_in_var_part = varsize_offsets_to_gcpointers_in_var_part

    def write_barrier(self, addr, addr_to, addr_struct):
        addr_to.address[0] = addr

    def free_memory(self):
        #this will never be called at runtime, just during setup
        "NOT_RPYTHON"
        pass

    def setup(self):
        pass

class DummyGC(GCBase):
    _alloc_flavor_ = "raw"

    def __init__(self, AddressLinkedList, dummy=None, get_roots=None):
        self.get_roots = get_roots
        #self.set_query_functions(None, None, None, None, None, None, None)
   
    def malloc(self, typeid, length=0):
        size = self.fixed_size(typeid)
        if self.is_varsize(typeid):
            size += length * self.varsize_item_sizes(typeid)
        return raw_malloc(size)
         
    def collect(self):
        self.get_roots() #this is there so that the annotator thinks get_roots is a function

    def size_gc_header(self, typeid=0):
        return 0

    def init_gc_object(self, addr, typeid):
        return
    init_gc_object_immortal = init_gc_object
   

class MarkSweepGC(GCBase):
    _alloc_flavor_ = "raw"
    
    _size_gc_header = gc_header_one_int

    def __init__(self, AddressLinkedList, start_heap_size=4096, get_roots=None):
        self.bytes_malloced = 0
        self.heap_size = start_heap_size
        #need to maintain a list of malloced objects, since we used the systems
        #allocator and can't walk the heap
        self.malloced_objects = None
        self.AddressLinkedList = AddressLinkedList
        #self.set_query_functions(None, None, None, None, None, None, None)
        self.get_roots = get_roots

    def setup(self):
        self.malloced_objects = self.AddressLinkedList()

    def malloc(self, typeid, length=0):
        if self.bytes_malloced > self.heap_size:
            self.collect()
        size = self.fixed_size(typeid)
        if self.is_varsize(typeid):
            itemsize = self.varsize_item_sizes(typeid)
            offset_to_length = self.varsize_offset_to_length(typeid)
            return self.malloc_varsize(typeid, length, size, itemsize, offset_to_length)
        return self.malloc_fixedsize(typeid, size)

    def malloc_fixedsize(self, typeid, size):
        if self.bytes_malloced > self.heap_size:
            self.collect()
        size_gc_header = MarkSweepGC._size_gc_header
        result = raw_malloc(size + size_gc_header)
        result.signed[0] = typeid << 1
        self.malloced_objects.append(result)
        self.bytes_malloced += size + size_gc_header
        return result + size_gc_header
         
    def malloc_varsize(self, typeid, length, size, itemsize, offset_to_length):
        if self.bytes_malloced > self.heap_size:
            self.collect()
        try:
            varsize = rarithmetic.ovfcheck(length * itemsize)
        except OverflowError:
            raise MemoryError
        size += varsize
        size_gc_header = MarkSweepGC._size_gc_header
        result = raw_malloc(size + size_gc_header)
        (result + offset_to_length + size_gc_header).signed[0] = length
        result.signed[0] = typeid << 1
        self.malloced_objects.append(result)
        self.bytes_malloced += size + size_gc_header
        return result + size_gc_header

    def collect(self):
        import os
        os.write(2, 'collecting... ')
        self.bytes_malloced = 0
        roots = self.get_roots()
        objects = self.AddressLinkedList()
        while 1:
            curr = roots.pop()
##             print "root: ", curr
            if curr == NULL:
                break
            # roots is a list of addresses to addresses:
            objects.append(curr.address[0])
            gc_info = curr.address[0] - MarkSweepGC._size_gc_header
            # constants roots are not malloced and thus don't have their mark
            # bit reset
            gc_info.signed[0] = gc_info.signed[0] & (~1)
        free_non_gc_object(roots)
        while 1:  #mark
            curr = objects.pop()
##             print "object: ", curr
            if curr == NULL:
                break
            gc_info = curr - MarkSweepGC._size_gc_header
            if gc_info.signed[0] & 1:
                continue
            typeid = gc_info.signed[0] >> 1
            offsets = self.offsets_to_gc_pointers(typeid)
            i = 0
            while i < len(offsets):
                pointer = curr + offsets[i]
                objects.append(pointer.address[0])
                i += 1
            if self.is_varsize(typeid):
                offset = self.varsize_offset_to_variable_part(
                    typeid)
                length = (curr + self.varsize_offset_to_length(typeid)).signed[0]
                offsets = self.varsize_offsets_to_gcpointers_in_var_part(typeid)
                itemlength = self.varsize_item_sizes(typeid)
                curr += offset
                i = 0
                while i < length:
                    item = curr + itemlength * i
                    j = 0
                    while j < len(offsets):
                        objects.append((item + offsets[j]).address[0])
                        j += 1
                    i += 1
            gc_info.signed[0] = gc_info.signed[0] | 1
        free_non_gc_object(objects)
        newmo = self.AddressLinkedList()
        curr_heap_size = 0
        freed_size = 0
        while 1:  #sweep
            curr = self.malloced_objects.pop()
            if curr == NULL:
                break
            typeid = curr.signed[0] >> 1
            size = self.fixed_size(typeid)
            if self.is_varsize(typeid):
                length = (curr + MarkSweepGC._size_gc_header + self.varsize_offset_to_length(typeid)).signed[0]
                size += length * self.varsize_item_sizes(typeid)
            if curr.signed[0] & 1:
                curr.signed[0] = curr.signed[0] & (~1)
                newmo.append(curr)
                curr_heap_size += size + MarkSweepGC._size_gc_header
            else:
                freed_size += size + MarkSweepGC._size_gc_header
                raw_free(curr)
        free_non_gc_object(self.malloced_objects)
        self.malloced_objects = newmo
        if curr_heap_size > self.heap_size:
            self.heap_size = curr_heap_size
        os.write(2, "freed %s bytes. the heap is now %s bytes.\n" % (freed_size, curr_heap_size))

    def size_gc_header(self, typeid=0):
        return MarkSweepGC._size_gc_header

    def init_gc_object(self, addr, typeid):
        addr.signed[0] = typeid << 1
    init_gc_object_immortal = init_gc_object

class SemiSpaceGC(GCBase):
    _alloc_flavor_ = "raw"

    def __init__(self, AddressLinkedList, space_size=1024*int_size,
                 get_roots=None):
        self.bytes_malloced = 0
        self.space_size = space_size
        self.tospace = NULL
        self.top_of_space = NULL
        self.fromspace = NULL
        self.free = NULL
        self.get_roots = get_roots

    def setup(self):
        self.tospace = raw_malloc(self.space_size)
        self.top_of_space = self.tospace + self.space_size
        self.fromspace = raw_malloc(self.space_size)
        self.free = self.tospace

    def free_memory(self):
        "NOT_RPYTHON"
        raw_free(self.tospace)
        self.tospace = NULL
        raw_free(self.fromspace)
        self.fromspace = NULL

    def malloc(self, typeid, length=0):
        size = self.fixed_size(typeid)
        if self.is_varsize(typeid):
            size += length * self.varsize_item_sizes(typeid)
        totalsize = size + self.size_gc_header()
        if self.free + totalsize > self.top_of_space:
            self.collect()
            #XXX need to increase the space size if the object is too big
            #for bonus points do big objects differently
            if self.free + totalsize > self.top_of_space:
                raise MemoryError
        result = self.free
        self.init_gc_object(result, typeid)
##         print "mallocing %s, size %s at %s" % (typeid, size, result)
        self.free += totalsize
        return result + self.size_gc_header()

    def collect(self):
##         print "collecting"
        tospace = self.fromspace
        fromspace = self.tospace
        self.fromspace = fromspace
        self.tospace = tospace
        self.top_of_space = tospace + self.space_size
        roots = self.get_roots()
        scan = self.free = tospace
        while 1:
            root = roots.pop()
            if root == NULL:
                break
##             print "root", root, root.address[0]
            root.address[0] = self.copy(root.address[0])
        free_non_gc_object(roots)
        while scan < self.free:
            curr = scan + self.size_gc_header()
            self.trace_and_copy(curr)
            scan += self.get_size(curr) + self.size_gc_header()

    def copy(self, obj):
        if not self.fromspace <= obj < self.fromspace + self.space_size:
            return self.copy_non_managed_obj(obj)
##         print "copying regularly", obj,
        if self.is_forwarded(obj):
##             print "already copied to", self.get_forwarding_address(obj)
            return self.get_forwarding_address(obj)
        else:
            newaddr = self.free
            totalsize = self.get_size(obj) + self.size_gc_header()
            raw_memcopy(obj - self.size_gc_header(), newaddr, totalsize)
            self.free += totalsize
            newobj = newaddr + self.size_gc_header()
##             print "to", newobj
            self.set_forwarding_address(obj, newobj)
            return newobj

    def copy_non_managed_obj(self, obj): #umph, PBCs, not really copy
##         print "copying nonmanaged", obj
        #we have to do the tracing here because PBCs are not moved to tospace
        self.trace_and_copy(obj)
        return obj

    def trace_and_copy(self, obj):
        gc_info = obj - self.size_gc_header()
        typeid = gc_info.signed[1]
##         print "scanning", obj, typeid
        offsets = self.offsets_to_gc_pointers(typeid)
        i = 0
        while i < len(offsets):
            pointer = obj + offsets[i]
            if pointer.address[0] != NULL:
                pointer.address[0] = self.copy(pointer.address[0])
            i += 1
        if self.is_varsize(typeid):
            offset = self.varsize_offset_to_variable_part(
                typeid)
            length = (obj + self.varsize_offset_to_length(typeid)).signed[0]
            offsets = self.varsize_offsets_to_gcpointers_in_var_part(typeid)
            itemlength = self.varsize_item_sizes(typeid)
            i = 0
            while i < length:
                item = obj + offset + itemlength * i
                j = 0
                while j < len(offsets):
                    pointer = item + offsets[j]
                    if pointer.address[0] != NULL:
                        pointer.address[0] = self.copy(pointer.address[0])
                    j += 1
                i += 1

    def is_forwarded(self, obj):
        return (obj - self.size_gc_header()).signed[1] < 0

    def get_forwarding_address(self, obj):
        return (obj - self.size_gc_header()).address[0]

    def set_forwarding_address(self, obj, newobj):
        gc_info = obj - self.size_gc_header()
        gc_info.signed[1] = -gc_info.signed[1] - 1
        gc_info.address[0] = newobj

    def get_size(self, obj):
        typeid = (obj - self.size_gc_header()).signed[1]
        size = self.fixed_size(typeid)
        if self.is_varsize(typeid):
            lenaddr = obj + self.varsize_offset_to_length(typeid)
            length = lenaddr.signed[0]
            size += length * self.varsize_item_sizes(typeid)
        return size


    def size_gc_header(self, typeid=0):
        return gc_header_two_ints

    def init_gc_object(self, addr, typeid):
        addr.signed[0] = 0
        addr.signed[1] = typeid
    init_gc_object_immortal = init_gc_object

class DeferredRefcountingGC(GCBase):
    _alloc_flavor_ = "raw"

    def __init__(self, AddressLinkedList, max_refcount_zero=50, get_roots=None):
        self.zero_ref_counts = None
        self.AddressLinkedList = AddressLinkedList
        self.length_zero_ref_counts = 0
        self.max_refcount_zero = max_refcount_zero
        #self.set_query_functions(None, None, None, None, None, None, None)
        self.get_roots = get_roots
        self.collecting = False

    def setup(self):
        self.zero_ref_counts = self.AddressLinkedList()
        

    def malloc(self, typeid, length=0):
        size = self.fixed_size(typeid)
        if self.is_varsize(typeid):
            size += length * self.varsize_item_sizes(typeid)
        size_gc_header = self.size_gc_header()
        result = raw_malloc(size + size_gc_header)
##         print "mallocing %s, size %s at %s" % (typeid, size, result)
        result.signed[0] = 0 # refcount
        result.signed[1] = typeid
        return result + size_gc_header

    def collect(self):
        if self.collecting:
            return
        else:
            self.collecting = True
        roots = self.get_roots()
        roots_copy = self.AddressLinkedList()
        curr = roots.pop()
        while curr != NULL:
##             print "root", root, root.address[0]
##             assert self.refcount(root.address[0]) >= 0, "refcount negative"
            self.incref(curr.address[0])
            roots_copy.append(curr)
            curr = roots.pop()
        roots = roots_copy
        dealloc_list = self.AddressLinkedList()
        self.length_zero_ref_counts = 0
        while 1:
            candidate = self.zero_ref_counts.pop()
            if candidate == NULL:
                break
            refcount = self.refcount(candidate)
            typeid = (candidate - self.size_gc_header()).signed[1]
            if (refcount == 0 and typeid >= 0):
                (candidate - self.size_gc_header()).signed[1] = -typeid - 1
                dealloc_list.append(candidate)
        while 1:
            deallocate = dealloc_list.pop()
            if deallocate == NULL:
                break
            typeid = (deallocate - self.size_gc_header()).signed[1]
            (deallocate - self.size_gc_header()).signed[1] = -typeid - 1
            self.deallocate(deallocate)
        free_non_gc_object(dealloc_list)
        while 1:
            root = roots.pop()
            if root == NULL:
                break
            self.decref(root.address[0])
        self.collecting = False

    def write_barrier(self, addr, addr_to, addr_struct):
        self.decref(addr_to.address[0])
        addr_to.address[0] = addr
        self.incref(addr)

    def deallocate(self, obj):
        gc_info = obj - self.size_gc_header()
        typeid = gc_info.signed[1]
##         print "deallocating", obj, typeid
        offsets = self.offsets_to_gc_pointers(typeid)
        i = 0
        while i < len(offsets):
            pointer = obj + offsets[i]
            self.decref(pointer.address[0])
            i += 1
        if self.is_varsize(typeid):
            offset = self.varsize_offset_to_variable_part(
                typeid)
            length = (obj + self.varsize_offset_to_length(typeid)).signed[0]
            offsets = self.varsize_offsets_to_gcpointers_in_var_part(typeid)
            itemlength = self.varsize_item_sizes(typeid)
            i = 0
            while i < length:
                item = obj + offset + itemlength * i
                j = 0
                while j < len(offsets):
                    pointer = item + offsets[j]
                    self.decref(pointer.address[0])
                    j += 1
                i += 1
        raw_free(gc_info)

    def incref(self, addr):
        if addr == NULL:
            return
        (addr - self.size_gc_header()).signed[0] += 1

    def decref(self, addr):
        if addr == NULL:
            return
        refcount = (addr - self.size_gc_header()).signed[0]
##         assert refcount > 0, "neg refcount"
        if refcount == 1:
            self.zero_ref_counts.append(addr)
            self.length_zero_ref_counts += 1
            if self.length_zero_ref_counts > self.max_refcount_zero:
                self.collect()
        (addr - self.size_gc_header()).signed[0] = refcount - 1

    def refcount(self, addr):
        return (addr - self.size_gc_header()).signed[0]

    def init_gc_object(self, addr, typeid):
        addr.signed[0] = 0 # refcount
        addr.signed[1] = typeid

    def init_gc_object_immortal(self, addr, typeid):
        addr.signed[0] = sys.maxint // 2 # refcount
        addr.signed[1] = typeid

    def size_gc_header(self, typeid=0):
        return gc_header_two_ints

