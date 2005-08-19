from pypy.rpython.memory.lladdress import raw_malloc, raw_free, NULL
from pypy.rpython.memory.support import AddressLinkedList
from pypy.rpython.memory import lltypesimulation
from pypy.rpython import lltype
from pypy.rpython.objectmodel import free_non_gc_object

import struct

class GCError(Exception):
    pass


class MarkSweepGC(object):
    _alloc_flavor_ = ""

    def __init__(self, objectmodel, collect_every_bytes):
        self.bytes_malloced = 0
        self.collect_every_bytes = collect_every_bytes
        #need to maintain a list of malloced objects, since we used the systems
        #allocator and can't walk the heap
        self.malloced_objects = AddressLinkedList()
        self.objectmodel = objectmodel

    def malloc(self, typeid, size):
        if self.bytes_malloced > self.collect_every_bytes:
            self.collect()
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
        roots = self.objectmodel.get_roots()
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
            offsets = self.objectmodel.offsets_to_gc_pointers(typeid)
            for i in range(len(offsets)):
                pointer = curr + offsets[i]
                objects.append(pointer.address[0])
                i += 1
            if self.objectmodel.is_varsize(typeid):
                offset = self.objectmodel.varsize_offset_to_variable_part(
                    typeid)
                length = (curr + self.objectmodel.varsize_offset_to_length(typeid)).signed[0]
                offsets = self.objectmodel.varsize_offsets_to_gcpointers_in_var_part(typeid)
                itemlength = self.objectmodel.varsize_item_sizes(typeid)
                curr += offset
                i = 0
                for i in range(length):
                    item = curr + itemlength * i
                    for j in range(len(offsets)):
                        objects.append((item + offsets[j]).address[0])
            gc_info.signed[0] = 1
        newmo = AddressLinkedList()
        while 1:  #sweep
            curr = self.malloced_objects.pop()
            if curr == NULL:
                break
            if curr.signed[0] == 1:
                curr.signed[0] = 0
                newmo.append(curr)
            else:
                raw_free(curr)
        free_non_gc_object(self.malloced_objects)
        self.malloced_objects = newmo

    def size_gc_header(self):
        return lltypesimulation.sizeof(lltype.Signed) * 2

    def init_gc_object(self, addr, typeid):
        addr.signed[0] = 0
        addr.signed[1] = typeid

