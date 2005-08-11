from pypy.rpython.memory.lladdress import raw_malloc, raw_free, NULL

import struct

INT_SIZE = struct.calcsize("i")

class AddressLinkedList(object):
    _raw_allocate_ = True
    def __init__(self):
        self.first = NULL
        self.last = NULL

    def append(self, addr):
        if addr == NULL:
            return
        new = raw_malloc(2 * INT_SIZE)
        if self.first == NULL:
            self.first = new
        else:
            self.last.address[0] = new
        self.last = new
        new.address[0] = NULL
        new.address[1] = addr
        
    def pop(self):
        if self.first == NULL:
            return NULL
        result = self.first.address[1]
        next = self.first.address[0]
        raw_free(self.first)
        self.first = next
        return result

    def free(self):
        while self.pop() != NULL:
            pass
