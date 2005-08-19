from pypy.rpython import lltype
from pypy.rpython.memory.support import AddressLinkedList, INT_SIZE
from pypy.rpython.memory.lladdress import raw_malloc, raw_free, NULL
from pypy.rpython.memory import lltypelayout
from pypy.rpython.memory import lltypesimulation
from pypy.rpython.memory.gc import MarkSweepGC

class LLInterpObjectModel(object):
    def __init__(self, llinterp, types,
                 type_to_typeid, constantroots):
        self.type_to_typeid = type_to_typeid
        self.constantroots = constantroots
        self.roots = []
        self.pseudo_root_pointers = NULL
        self.llinterp = llinterp
        self.types = types
        self._is_varsize = []
        self._offsets_to_gc_pointers = []
        self._varsize_item_sizes = []
        self._varsize_offset_to_variable_part = []
        self._varsize_offset_to_length = []
        self._varsize_offsets_to_gcpointers_in_var_part = []
        tttid = zip(*zip(*type_to_typeid.items())[::-1])
        tttid.sort()
        tttid = zip(*zip(*tttid)[::-1])
        for TYPE, typeid in tttid:
            varsize = (isinstance(TYPE, lltype.Array) or
                       (isinstance(TYPE, lltype.Struct) and
                        TYPE._arrayfld is not None))
            self._is_varsize.append(varsize)
            self._offsets_to_gc_pointers.append(
                lltypelayout.offsets_to_gc_pointers(TYPE))
            if varsize:
                self._varsize_item_sizes.append(
                    lltypelayout.get_variable_size(TYPE))
                self._varsize_offset_to_variable_part.append(
                    lltypelayout.get_fixed_size(TYPE))
                self._varsize_offset_to_length.append(
                    lltypelayout.varsize_offset_to_length(TYPE))
                self._varsize_offsets_to_gcpointers_in_var_part.append(
                    lltypelayout.varsize_offsets_to_gcpointers_in_var_part(TYPE))
            else:
                self._varsize_item_sizes.append(0)
                self._varsize_offset_to_variable_part.append(0)
                self._varsize_offset_to_length.append(0)
                self._varsize_offsets_to_gcpointers_in_var_part.append([])

    def update_changed_addresses(self):
        for i, root in enumerate(self.roots):
            if root._address != self.pseudo_root_pointers.address[i]:
                print "address changed:", root._address, self.pseudo_root_pointers.address[i]
            root.__dict__['_address'] = self.pseudo_root_pointers.address[i]

    def get_typeid(self, TYPE):
        typeid = self.type_to_typeid[TYPE]
        return typeid

    def is_varsize(self, typeid):
        return self._is_varsize[typeid]

    def offsets_to_gc_pointers(self, typeid):
        return self._offsets_to_gc_pointers[typeid]

    def varsize_item_sizes(self, typeid):
        return self._varsize_item_sizes[typeid]

    def varsize_offset_to_variable_part(self, typeid):
        return self._varsize_offset_to_variable_part[typeid]

    def varsize_offset_to_length(self, typeid):
        return self._varsize_offset_to_length[typeid]

    def varsize_offsets_to_gcpointers_in_var_part(self, typeid):
        return self._varsize_offsets_to_gcpointers_in_var_part[typeid]

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
