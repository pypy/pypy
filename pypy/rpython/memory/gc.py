from pypy.rpython.memory.lladdress import raw_malloc, raw_free, raw_memcopy
from pypy.rpython.memory.lladdress import NULL
from pypy.rpython.memory.support import AddressLinkedList
from pypy.rpython.memory import lltypesimulation
from pypy.rpython import lltype
from pypy.rpython.objectmodel import free_non_gc_object

import struct

class GCError(Exception):
    pass

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
        

class MarkSweepGC(GCBase):
    _alloc_flavor_ = "raw"

    def __init__(self, start_heap_size, get_roots, is_varsize,
                 offsets_to_gc_pointers, fixed_size, varsize_item_sizes,
                 varsize_offset_to_variable_part, varsize_offset_to_length,
                 varsize_offsets_to_gcpointers_in_var_part):
        self.bytes_malloced = 0
        self.heap_size = start_heap_size
        #need to maintain a list of malloced objects, since we used the systems
        #allocator and can't walk the heap
        self.malloced_objects = AddressLinkedList()
        self.is_varsize = is_varsize
        self.offsets_to_gc_pointers = offsets_to_gc_pointers
        self.fixed_size = fixed_size
        self.varsize_item_sizes = varsize_item_sizes
        self.varsize_offset_to_variable_part = varsize_offset_to_variable_part
        self.varsize_offset_to_length = varsize_offset_to_length
        self.varsize_offsets_to_gcpointers_in_var_part = varsize_offsets_to_gcpointers_in_var_part
        self.get_roots = get_roots

    def malloc(self, typeid, length=0):
        if self.bytes_malloced > self.heap_size:
            self.collect()
        size = self.fixed_size(typeid)
        if self.is_varsize(typeid):
            size += length * self.varsize_item_sizes(typeid)
        size_gc_header = self.size_gc_header()
        result = raw_malloc(size + size_gc_header)
        print "mallocing %s, size %s at %s" % (typeid, size, result)
        self.init_gc_object(result, typeid)
        self.malloced_objects.append(result)
        self.bytes_malloced += size + size_gc_header
        return result + size_gc_header

    def collect(self):
        print "collecting"
        self.bytes_malloced = 0
        roots = self.get_roots()
        objects = AddressLinkedList()
        while 1:
            curr = roots.pop()
            print "root: ", curr
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
            print "object: ", curr
            if curr == NULL:
                break
            gc_info = curr - self.size_gc_header()
            if gc_info.signed[0] == 1:
                continue
            typeid = gc_info.signed[1]
            offsets = self.offsets_to_gc_pointers(typeid)
            for i in range(len(offsets)):
                pointer = curr + offsets[i]
                objects.append(pointer.address[0])
            if self.is_varsize(typeid):
                offset = self.varsize_offset_to_variable_part(
                    typeid)
                length = (curr + self.varsize_offset_to_length(typeid)).signed[0]
                offsets = self.varsize_offsets_to_gcpointers_in_var_part(typeid)
                itemlength = self.varsize_item_sizes(typeid)
                curr += offset
                for i in range(length):
                    item = curr + itemlength * i
                    for j in range(len(offsets)):
                        objects.append((item + offsets[j]).address[0])
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
        print "free %s bytes. the heap is %s bytes." % (freed_size, curr_heap_size)
        free_non_gc_object(self.malloced_objects)
        self.malloced_objects = newmo
        if curr_heap_size > self.heap_size:
            self.heap_size = curr_heap_size

    def size_gc_header(self, typeid=0):
        return lltypesimulation.sizeof(lltype.Signed) * 2

    def init_gc_object(self, addr, typeid):
        addr.signed[0] = 0
        addr.signed[1] = typeid


class SemiSpaceGC(GCBase):
    _alloc_flavor_ = "raw"

    def __init__(self, space_size, get_roots, is_varsize,
                 offsets_to_gc_pointers, fixed_size, varsize_item_sizes,
                 varsize_offset_to_variable_part, varsize_offset_to_length,
                 varsize_offsets_to_gcpointers_in_var_part):
        self.bytes_malloced = 0
        self.space_size = space_size
        self.tospace = raw_malloc(space_size)
        self.top_of_space = self.tospace + space_size
        self.fromspace = raw_malloc(space_size)
        self.free = self.tospace
        self.is_varsize = is_varsize
        self.offsets_to_gc_pointers = offsets_to_gc_pointers
        self.fixed_size = fixed_size
        self.varsize_item_sizes = varsize_item_sizes
        self.varsize_offset_to_variable_part = varsize_offset_to_variable_part
        self.varsize_offset_to_length = varsize_offset_to_length
        self.varsize_offsets_to_gcpointers_in_var_part = varsize_offsets_to_gcpointers_in_var_part
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
        print "mallocing %s, size %s at %s" % (typeid, size, result)
        self.free += totalsize
        return result + self.size_gc_header()


    def collect(self):
        print "collecting"
        self.fromspace, self.tospace = self.tospace, self.fromspace
        self.top_of_space = self.tospace + self.space_size
        roots = self.get_roots()
        scan = self.free = self.tospace
        while 1:
            root = roots.pop()
            if root == NULL:
                break
            print "root", root, root.address[0]
            root.address[0] = self.copy(root.address[0])
        while scan < self.free:
            curr = scan + self.size_gc_header()
            self.trace_and_copy(curr)
            scan += self.get_size(curr) + self.size_gc_header()

    def copy(self, obj):
        if not self.fromspace <= obj < self.fromspace + self.space_size:
            return self.copy_non_managed_obj(obj)
        print "copying regularly", obj,
        if self.is_forwared(obj):
            print "already copied to", self.get_forwarding_address(obj)
            return self.get_forwarding_address(obj)
        else:
            newaddr = self.free
            totalsize = self.get_size(obj) + self.size_gc_header()
            raw_memcopy(obj - self.size_gc_header(), newaddr, totalsize)
            self.free += totalsize
            newobj = newaddr + self.size_gc_header()
            print "to", newobj
            self.set_forwarding_address(obj, newobj)
            return newobj

    def copy_non_managed_obj(self, obj): #umph, PBCs, not really copy
        print "copying nonmanaged", obj
        #we have to do the tracing here because PBCs are not moved to tospace
        self.trace_and_copy(obj)
        return obj

    def trace_and_copy(self, obj):
        gc_info = obj - self.size_gc_header()
        typeid = gc_info.signed[1]
        print "scanning", obj, typeid
        offsets = self.offsets_to_gc_pointers(typeid)
        for i in range(len(offsets)):
            pointer = obj + offsets[i]
            if pointer.address[0] != NULL:
                pointer.address[0] = self.copy(pointer.address[0])
        if self.is_varsize(typeid):
            offset = self.varsize_offset_to_variable_part(
                typeid)
            length = (obj + self.varsize_offset_to_length(typeid)).signed[0]
            offsets = self.varsize_offsets_to_gcpointers_in_var_part(typeid)
            itemlength = self.varsize_item_sizes(typeid)
            for i in range(length):
                item = obj + offset + itemlength * i
                for j in range(len(offsets)):
                    pointer = item + offsets[j]
                    if pointer.address[0] != NULL:
                        pointer.address[0] = self.copy(pointer.address[0])

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
        return lltypesimulation.sizeof(lltype.Signed) * 2

    def init_gc_object(self, addr, typeid):
        addr.signed[0] = 0
        addr.signed[1] = typeid
