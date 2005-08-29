from pypy.translator.annrpython import RPythonAnnotator
from pypy.rpython import lltype
from pypy.rpython.memory.support import AddressLinkedList, INT_SIZE
from pypy.rpython.memory.lladdress import raw_malloc, raw_free, NULL
from pypy.rpython.memory import lltypelayout
from pypy.rpython.memory import lltypesimulation
from pypy.rpython.memory import gc

class QueryTypes(object):
    def __init__(self, llinterp):
        self.llinterp = llinterp
        self.types = []
        self.type_to_typeid = {}

    def get_typeid(self, TYPE):
        if TYPE not in self.type_to_typeid:
            index = len(self.types)
            self.type_to_typeid[TYPE] = index
            self.types.append(TYPE)
            return index
        typeid = self.type_to_typeid[TYPE]
        return typeid

    def create_query_functions(self):
        _is_varsize = []
        _offsets_to_gc_pointers = []
        _fixed_size = []
        _varsize_item_sizes = []
        _varsize_offset_to_variable_part = []
        _varsize_offset_to_length = []
        _varsize_offsets_to_gcpointers_in_var_part = []
        tttid = zip(*zip(*self.type_to_typeid.items())[::-1])
        tttid.sort()
        tttid = zip(*zip(*tttid)[::-1])
        for TYPE, typeid in tttid:
            varsize = (isinstance(TYPE, lltype.Array) or
                       (isinstance(TYPE, lltype.Struct) and
                        TYPE._arrayfld is not None))
            _is_varsize.append(varsize)
            _offsets_to_gc_pointers.append(
                lltypelayout.offsets_to_gc_pointers(TYPE))
            _fixed_size.append(lltypelayout.get_fixed_size(TYPE))
            if varsize:
                _varsize_item_sizes.append(lltypelayout.get_variable_size(TYPE))
                _varsize_offset_to_variable_part.append(
                    lltypelayout.get_fixed_size(TYPE))
                _varsize_offset_to_length.append(
                    lltypelayout.varsize_offset_to_length(TYPE))
                _varsize_offsets_to_gcpointers_in_var_part.append(
                    lltypelayout.varsize_offsets_to_gcpointers_in_var_part(TYPE))
            else:
                _varsize_item_sizes.append(0)
                _varsize_offset_to_variable_part.append(0)
                _varsize_offset_to_length.append(0)
                _varsize_offsets_to_gcpointers_in_var_part.append([])
        def is_varsize(typeid):
            return _is_varsize[typeid]
        def offsets_to_gc_pointers(typeid):
            return _offsets_to_gc_pointers[typeid]
        def fixed_size(typeid):
            return _fixed_size[typeid]
        def varsize_item_sizes(typeid):
            return _varsize_item_sizes[typeid]
        def varsize_offset_to_variable_part(typeid):
            return _varsize_offset_to_variable_part[typeid]
        def varsize_offset_to_length(typeid):
            return _varsize_offset_to_length[typeid]
        def varsize_offsets_to_gcpointers_in_var_part(typeid):
            return _varsize_offsets_to_gcpointers_in_var_part[typeid]
        return (is_varsize, offsets_to_gc_pointers, fixed_size,
                varsize_item_sizes, varsize_offset_to_variable_part,
                varsize_offset_to_length,
                varsize_offsets_to_gcpointers_in_var_part)

    def is_varsize(self, typeid):
        assert typeid >= 0
        TYPE = self.types[typeid]
        return (isinstance(TYPE, lltype.Array) or
                (isinstance(TYPE, lltype.Struct) and
                 TYPE._arrayfld is not None))

    def offsets_to_gc_pointers(self, typeid):
        assert typeid >= 0
        return lltypelayout.offsets_to_gc_pointers(self.types[typeid])

    def fixed_size(self, typeid):
        assert typeid >= 0
        return lltypelayout.get_fixed_size(self.types[typeid])

    def varsize_item_sizes(self, typeid):
        assert typeid >= 0
        if self.is_varsize(typeid):
            return lltypelayout.get_variable_size(self.types[typeid])
        else:
            return 0

    def varsize_offset_to_variable_part(self, typeid):
        assert typeid >= 0
        if self.is_varsize(typeid):
            return lltypelayout.get_fixed_size(self.types[typeid])
        else:
            return 0

    def varsize_offset_to_length(self, typeid):
        assert typeid >= 0
        if self.is_varsize(typeid):
            return lltypelayout.varsize_offset_to_length(self.types[typeid])
        else:
            return 0

    def varsize_offsets_to_gcpointers_in_var_part(self, typeid):
        assert typeid >= 0
        if self.is_varsize(typeid):
            return lltypelayout.varsize_offsets_to_gcpointers_in_var_part(
                self.types[typeid])
        else:
            return 0

    def get_setup_query_functions(self):
        return (self.is_varsize, self.offsets_to_gc_pointers, self.fixed_size,
                self.varsize_item_sizes, self.varsize_offset_to_variable_part,
                self.varsize_offset_to_length,
                self.varsize_offsets_to_gcpointers_in_var_part)


class GcWrapper(object):
    def __init__(self, llinterp, gc, qt, constantroots):
        self.llinterp = llinterp
        self.gc = gc
        self.gc.get_roots = self.get_roots
        self.query_types = qt
        self.constantroots = constantroots
        self.pseudo_root_pointers = NULL
        self.roots = []

    def get_arg_malloc(self, TYPE, size=0):
        typeid = self.query_types.get_typeid(TYPE)
        return [typeid, size]

    def get_funcptr_malloc(self):
        return self.llinterp.llt.functionptr(gc.gc_interface["malloc"], "malloc",
                                             _callable=self.gc.malloc)

    def adjust_result_malloc(self, address, TYPE, size=0):
        result = lltypesimulation.init_object_on_address(address, TYPE, size)
        self.update_changed_addresses()
        return result

    def update_changed_addresses(self):
        for i, root in enumerate(self.roots):
            if root._address != self.pseudo_root_pointers.address[i]:
                print "address changed:", root._address, self.pseudo_root_pointers.address[i]
            root.__dict__['_address'] = self.pseudo_root_pointers.address[i]

    def get_roots(self):
        print "getting roots"
        if self.pseudo_root_pointers != NULL:
            raw_free(self.pseudo_root_pointers)
        self.roots = self.llinterp.find_roots() + self.constantroots
        self.roots = [r for r in self.roots
                          if isinstance(r._TYPE.TO,
                                        (lltype.Struct, lltype.Array))]
        if len(self.roots) == 0:
            self.pseudo_root_pointers = NULL
        else:
            self.pseudo_root_pointers = raw_malloc(len(self.roots) * INT_SIZE)
        ll = AddressLinkedList()
        for i, root in enumerate(self.roots):
            self.pseudo_root_pointers.address[i] = root._address
            ll.append(self.pseudo_root_pointers + INT_SIZE * i)
        return ll

class AnnotatingGcWrapper(GcWrapper):
    def __init__(self, llinterp, gc, qt, constantroots):
        super(AnnotatingGcWrapper, self).__init__(llinterp, gc, qt,
                                                  constantroots)
        self.annotate_rtype_gc()

    def annotate_rtype_gc(self):
        #XXXXX unfinished
        func = gc.get_dummy_annotate(self.gc)
        self.gc.get_roots = gc.dummy_get_roots
        a = RPythonAnnotator()
        res = a.build_types(func, [])
        a.translator.view()
        a.translator.specialize()
        self.gc.get_roots = self.get_roots
