from pypy.rpython.memory.lladdress import raw_malloc, raw_free, raw_memcopy
from pypy.rpython.memory.lladdress import NULL, address, Address
from pypy.rpython.memory.support import AddressLinkedList
from pypy.rpython.memory import lltypesimulation
from pypy.rpython import lltype
from pypy.rpython.objectmodel import free_non_gc_object

int_size = lltypesimulation.sizeof(lltype.Signed)

class GCError(Exception):
    pass

def get_dummy_annotate(gc):
    def dummy_annotate():
        gc.get_roots = dummy_get_roots1 #prevent the get_roots attribute to 
        gc.get_roots = dummy_get_roots2 #be constants
        a = gc.malloc(1, 2)
        b = gc.malloc(2, 3)
        gc.collect()
        return a - b
    return dummy_annotate

gc_interface = {
    "malloc": lltype.FuncType((lltype.Signed, lltype.Signed), lltype.Signed),
    "collect": lltype.FuncType((), lltype.Void),
    "write_barrier": lltype.FuncType((Address, ) * 3, lltype.Void),
    }

def dummy_get_roots1():
    ll = AddressLinkedList()
    ll.append(NULL)
    ll.append(raw_malloc(10))
    return ll

def dummy_get_roots2():
    ll = AddressLinkedList()
    ll.append(raw_malloc(10))
    ll.append(NULL)
    return ll


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

class MarkSweepGC(GCBase):
    _alloc_flavor_ = "raw"

    def __init__(self, start_heap_size=4096, get_roots=None):
        self.bytes_malloced = 0
        self.heap_size = start_heap_size
        #need to maintain a list of malloced objects, since we used the systems
        #allocator and can't walk the heap
        self.malloced_objects = AddressLinkedList()
        self.set_query_functions(None, None, None, None, None, None, None)
        self.get_roots = get_roots

    def malloc(self, typeid, length=0):
        if self.bytes_malloced > self.heap_size:
            self.collect()
        size = self.fixed_size(typeid)
        if self.is_varsize(typeid):
            size += length * self.varsize_item_sizes(typeid)
        size_gc_header = self.size_gc_header()
        result = raw_malloc(size + size_gc_header)
##         print "mallocing %s, size %s at %s" % (typeid, size, result)
        self.init_gc_object(result, typeid)
        self.malloced_objects.append(result)
        self.bytes_malloced += size + size_gc_header
        return result + size_gc_header

    def collect(self):
##         print "collecting"
        self.bytes_malloced = 0
        roots = self.get_roots()
        objects = AddressLinkedList()
        while 1:
            curr = roots.pop()
##             print "root: ", curr
            if curr == NULL:
                break
            # roots is a list of addresses to addresses:
            objects.append(curr.address[0])
            gc_info = curr.address[0] - self.size_gc_header()
            # constants roots are not malloced and thus don't have their mark
            # bit reset
            gc_info.signed[0] = 0 
        while 1:  #mark
            curr = objects.pop()
##             print "object: ", curr
            if curr == NULL:
                break
            gc_info = curr - self.size_gc_header()
            if gc_info.signed[0] == 1:
                continue
            typeid = gc_info.signed[1]
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
            gc_info.signed[0] = 1
        newmo = AddressLinkedList()
        curr_heap_size = 0
        freed_size = 0
        while 1:  #sweep
            curr = self.malloced_objects.pop()
            if curr == NULL:
                break
            typeid = curr.signed[1]
            size = self.fixed_size(typeid)
            if self.is_varsize(typeid):
                length = (curr + self.size_gc_header() + self.varsize_offset_to_length(typeid)).signed[0]
                size += length * self.varsize_item_sizes(typeid)
            if curr.signed[0] == 1:
                curr.signed[0] = 0
                newmo.append(curr)
                curr_heap_size += size + self.size_gc_header()
            else:
                freed_size += size + self.size_gc_header()
                raw_free(curr)
##         print "free %s bytes. the heap is %s bytes." % (freed_size, curr_heap_size)
        free_non_gc_object(self.malloced_objects)
        self.malloced_objects = newmo
        if curr_heap_size > self.heap_size:
            self.heap_size = curr_heap_size

    def size_gc_header(self, typeid=0):
        return int_size * 2

    def init_gc_object(self, addr, typeid):
        addr.signed[0] = 0
        addr.signed[1] = typeid


class SemiSpaceGC(GCBase):
    _alloc_flavor_ = "raw"

    def __init__(self, space_size=4096, get_roots=None):
        self.bytes_malloced = 0
        self.space_size = space_size
        self.tospace = raw_malloc(space_size)
        self.top_of_space = self.tospace + space_size
        self.fromspace = raw_malloc(space_size)
        self.free = self.tospace
        self.set_query_functions(None, None, None, None, None, None, None)
        self.get_roots = get_roots

    def malloc(self, typeid, length=0):
        size = self.fixed_size(typeid)
        if self.is_varsize(typeid):
            size += length * self.varsize_item_sizes(typeid)
        totalsize = size + self.size_gc_header()
        if self.free + totalsize > self.top_of_space:
            self.collect()
            #XXX need to increase the space size if the object is too big
            #for bonus points do big blocks differently
            return self.malloc(typeid, length)
        result = self.free
        self.init_gc_object(result, typeid)
##         print "mallocing %s, size %s at %s" % (typeid, size, result)
        self.free += totalsize
        return result + self.size_gc_header()


    def collect(self):
##         print "collecting"
        self.fromspace, self.tospace = self.tospace, self.fromspace
        self.top_of_space = self.tospace + self.space_size
        roots = self.get_roots()
        scan = self.free = self.tospace
        while 1:
            root = roots.pop()
            if root == NULL:
                break
##             print "root", root, root.address[0]
            root.address[0] = self.copy(root.address[0])
        while scan < self.free:
            curr = scan + self.size_gc_header()
            self.trace_and_copy(curr)
            scan += self.get_size(curr) + self.size_gc_header()

    def copy(self, obj):
        if not self.fromspace <= obj < self.fromspace + self.space_size:
            return self.copy_non_managed_obj(obj)
##         print "copying regularly", obj,
        if self.is_forwared(obj):
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

    def is_forwared(self, obj):
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
        return int_size * 2

    def init_gc_object(self, addr, typeid):
        addr.signed[0] = 0
        addr.signed[1] = typeid


class DeferredRefcountingGC(GCBase):
    _alloc_flavor_ = "raw"

    def __init__(self, max_refcount_zero=10, get_roots=None):
        self.zero_ref_counts = AddressLinkedList()
        self.length_zero_ref_counts = 0
        self.max_refcount_zero = max_refcount_zero
        self.set_query_functions(None, None, None, None, None, None, None)
        self.get_roots = get_roots

    def malloc(self, typeid, length=0):
        size = self.fixed_size(typeid)
        if self.is_varsize(typeid):
            size += length * self.varsize_item_sizes(typeid)
        size_gc_header = self.size_gc_header()
        result = raw_malloc(size + size_gc_header)
        print "mallocing %s, size %s at %s" % (typeid, size, result)
        self.init_gc_object(result, typeid)
        return result + size_gc_header

    def collect(self):
        roots = self.get_roots()
        curr = roots.first
        while 1:
            root = curr.address[1]
            print "root", root, root.address[0]
            self.incref(root.address[0])
            if curr.address[0] == NULL:
                break
            curr = curr.address[0]
        while 1:
            candidate = self.zero_ref_counts.pop()
            self.length_zero_ref_counts -= 1
            if candidate == NULL:
                break
            refcount = self.refcount(candidate)
            if refcount == 0:
                self.deallocate(candidate)
        while 1:
            root = roots.pop()
            if root == NULL:
                break
            print "root", root, root.address[0]
            self.decref(root.address[0])

    def write_barrier(self, addr, addr_to, addr_struct):
        self.decref(addr_to.address[0])
        addr_to.address[0] = addr
        self.incref(addr)

    def deallocate(self, addr):
        gc_info = obj - self.size_gc_header()
        typeid = gc_info.signed[1]
        print "deallocating", obj, typeid
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
        raw_free(addr)

    def incref(self, addr):
        (addr - self.size_gc_header()).signed[0] += 1

    def decref(self, addr):
        if addr == NULL:
            return
        refcount = (addr - self.size_gc_header()).signed[0]
        if refcount == 1:
            self.zero_ref_counts.append(addr)
            self.length_zero_ref_counts += 1
            if self.length_zero_ref_counts > self.max_refcount_zero:
                self.collect()
        (addr - self.size_gc_header()).signed[0] = refcount - 1
        assert refcount > 0

    def refcount(self, addr):
        (addr - self.size_gc_header()).signed[0]

    def init_gc_object(self, addr, typeid):
        addr.signed[0] = 0 # refcount
        addr.signed[1] = typeid

    def size_gc_header(self, typeid=0):
        return int_size * 2

