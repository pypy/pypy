from pypy.rpython import lltype
from pypy.rpython.memory.support import AddressLinkedList, INT_SIZE
from pypy.rpython.memory.lladdress import raw_malloc, raw_free, NULL
from pypy.rpython.memory import lltypesimulation
from pypy.rpython.memory.gc import MarkSweepGC

class LLInterpObjectModel(object):
    def __init__(self, llinterp):
        self.type_to_typeid = {}
        self.types = []
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

    def get_roots(self):
        print "getting roots"
        if self.pseudo_root_pointers != NULL:
            raw_free(self.pseudo_root_pointers)
        self.roots = self.llinterp.find_roots()
        print "found:", self.roots
        self.pseudo_root_pointers = raw_malloc(len(self.roots) * INT_SIZE)
        ll = AddressLinkedList()
        for i, root in enumerate(self.roots):
            self.pseudo_root_pointers.address[i] = root._address
            ll.append(self.pseudo_root_pointers + INT_SIZE * i)
        return ll

    def get_contained_pointers(self, addr, typeid):
        TYPE = self.types[typeid]
        if isinstance(TYPE, lltype.Struct):
            offsets = self.get_contained_pointers_struct(addr, TYPE)
        elif isinstance(TYPE, lltype.Array):
            offsets = self.get_contained_pointers_array(addr, TYPE)
        ll = AddressLinkedList()
        for offset in offsets:
            ll.append(addr + offset)
        print "for the TYPE %s if found the follwing offsets: %s" % (TYPE, offsets)
        return ll

    def get_contained_pointers_struct(self, addr, TYPE, offset=0):
        offsets = []
        substructures = [(TYPE, offset)]
        while len(substructures):
            TYPE, offset = substructures.pop()
            layout = lltypesimulation.get_layout(TYPE)
            for name in TYPE._names:
                FIELD = getattr(TYPE, name)
                if isinstance(FIELD, lltype.Ptr) and FIELD._needsgc():
                    offsets.append(offset + layout[name])
                elif isinstance(FIELD, lltype.Struct):
                    substructures.append((FIELD, layout[name] + offset))
                elif isinstance(FIELD, lltype.Array):
                    assert offset == 0 #can only inline into outermost struct
                    baseaddr = addr + layout[name]
                    offsets += self.get_contained_pointers_array(
                        baseaddr, FIELD, layout[name])
        return offsets

    def get_contained_pointers_array(self, addr, TYPE, offset=0):
        offsets = []
        length = addr.signed[0]
        itemsize = lltypesimulation.get_variable_size(TYPE)
        if isinstance(TYPE.OF, lltype.Ptr) and TYPE.OF._needsgc():
            for i in range(length):
                offsets.append(offset + INT_SIZE + i * itemsize)
        elif isinstance(TYPE.OF, lltype.GcStruct):
            for i in range(length):
                item_offset = INT_SIZE + i * itemsize
                offsets += self.get_contained_pointers_array(
                    TYPE.OF, addr + item_offset, offset + item_offset)
        return offsets

class GcWrapper(object):
    def __init__(self, llinterp, gc):
        self.llinterp = llinterp
        self.objectmodel = gc.objectmodel
        assert isinstance(self.objectmodel, LLInterpObjectModel)
        self.gc = gc

    def malloc(self, TYPE, size=0):
        typeid = self.objectmodel.get_typeid(TYPE)
        address = self.gc.malloc(typeid,
                                 lltypesimulation.get_total_size(TYPE, size))
        result = lltypesimulation.simulatorptr(lltype.Ptr(TYPE), address)
        result._zero_initialize(size)
        result._init_size(size)
        self.objectmodel.update_changed_addresses()
        return result
