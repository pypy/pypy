from pypy.rpython.memory.lladdress import raw_malloc, raw_free, NULL
from pypy.rpython.memory.support import AddressLinkedList
import struct

INT_SIZE = struct.calcsize("i")

class GCError(Exception):
    pass

class FREED_OBJECT(object):
    def __getattribute__(self, attr):
        raise GCError("trying to access freed object")
    def __setattribute__(self, attr, value):
        raise GCError("trying to access freed object")


def free_non_gc_object(obj):
    assert getattr(obj.__class__, "_raw_allocate_", False), "trying to free regular object"
    obj.__dict__ = {}
    obj.__class__ = FREED_OBJECT


class MarkSweepGC(object):
    _raw_allocate_ = True
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
        result = raw_malloc(size + 2 * INT_SIZE)
        print "mallocing %s, size %s at %s" % (typeid, size, result)
        print "real size: %s" % (size + 2 * INT_SIZE, )
        result.signed[0] = 0
        result.signed[1] = typeid
        self.malloced_objects.append(result)
        self.bytes_malloced += size + 2 * INT_SIZE
        return result + 2 * INT_SIZE

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
            gc_info = curr.address[0] - 2 * INT_SIZE
            assert gc_info.signed[0] == 0
        while 1:  #mark
            curr = objects.pop()
            print "object: ", curr
            if curr == NULL:
                break
            gc_info = curr - 2 * INT_SIZE
            if gc_info.signed[0] == 1:
                continue
            pointers = self.objectmodel.get_contained_pointers(
                curr, gc_info.signed[1])
            while 1:
                pointer = pointers.pop()
                if pointer == NULL:
                    break
                objects.append(pointer)
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
