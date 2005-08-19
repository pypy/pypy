from pypy.rpython import lltype
from pypy.rpython.memory.support import AddressLinkedList, INT_SIZE
from pypy.rpython.memory.lladdress import raw_malloc, raw_free, NULL
from pypy.rpython.memory import lltypesimulation
from pypy.rpython.memory.gc import MarkSweepGC

class LLInterpObjectModel(object):
    def __init__(self, llinterp, types, type_to_typeid, constantroots):
        self.types = types
        self.type_to_typeid = type_to_typeid
        self.constantroots = constantroots
        self.roots = []
        self.pseudo_root_pointers = NULL
        self.llinterp = llinterp

    def update_changed_addresses(self):
        for i, root in enumerate(self.roots):
            if root._address != self.pseudo_root_pointers.address[i]:
                print "address changed:", root._address, self.pseudo_root_pointers.address[i]
            root.__dict__['_address'] = self.pseudo_root_pointers.address[i]

    def get_typeid(self, TYPE):
        if TYPE not in self.type_to_typeid:
            index = len(self.types)
            self.type_to_typeid[TYPE] = index
            self.types.append(TYPE)
        typeid = self.type_to_typeid[TYPE]
        return typeid

    def get_contained_pointers(self, addr, typeid):
        TYPE = self.types[typeid]
        ptr = lltypesimulation.simulatorptr(lltype.Ptr(TYPE), addr)
        ll = AddressLinkedList()
        offsets = ptr.get_offsets_of_contained_pointers()
        for offset in offsets:
            ll.append(addr + offset)
        return ll

    def get_roots(self):
        print "getting roots"
        if self.pseudo_root_pointers != NULL:
            raw_free(self.pseudo_root_pointers)
        self.roots = self.llinterp.find_roots() + self.constantroots
        print "found:", self.roots
        if len(self.roots) == 0:
            self.pseudo_root_pointers = NULL
        else:
            self.pseudo_root_pointers = raw_malloc(len(self.roots) * INT_SIZE)
        ll = AddressLinkedList()
        for i, root in enumerate(self.roots):
            self.pseudo_root_pointers.address[i] = root._address
            ll.append(self.pseudo_root_pointers + INT_SIZE * i)
        return ll


class GcWrapper(object):
    def __init__(self, llinterp, gc):
        self.llinterp = llinterp
        self.objectmodel = gc.objectmodel
        assert isinstance(self.objectmodel, LLInterpObjectModel)
        self.gc = gc

    def malloc(self, TYPE, size=0):
        typeid = self.objectmodel.get_typeid(TYPE)
        address = self.gc.malloc(typeid,
                                 lltypesimulation.sizeof(TYPE, size))
        return lltypesimulation.init_object_on_address(address, TYPE, size)
        self.objectmodel.update_changed_addresses()
        return result
