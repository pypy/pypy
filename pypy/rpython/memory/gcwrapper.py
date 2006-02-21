from pypy.annotation.annrpython import RPythonAnnotator
from pypy.rpython.rtyper import RPythonTyper
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.memory.support import AddressLinkedList, INT_SIZE
from pypy.rpython.memory.lladdress import raw_malloc, raw_free, NULL
from pypy.rpython.memory import lltypelayout
from pypy.rpython.memory import lltypesimulation
from pypy.rpython.memory import gc
from pypy.rpython.memory.convertlltype import FlowGraphConstantConverter

class QueryTypes(object):
    def __init__(self):
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
            varsize = self.is_varsize(typeid)
            _is_varsize.append(varsize)
            _offsets_to_gc_pointers.append(self.offsets_to_gc_pointers(typeid))
            _fixed_size.append(self.fixed_size(typeid))
            if varsize:
                _varsize_item_sizes.append(self.varsize_item_sizes(typeid))
                _varsize_offset_to_variable_part.append(
                    self.varsize_offset_to_variable_part(typeid))
                _varsize_offset_to_length.append(
                    self.varsize_offset_to_length(typeid))
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

class SymbolicQueryTypes(QueryTypes):
    def fixed_size(self, typeid):
        assert typeid >= 0
        if self.types[typeid]._is_varsize():
            return llmemory.sizeof(self.types[typeid], 0)
        else:
            return llmemory.sizeof(self.types[typeid])

    def varsize_item_sizes(self, typeid):
        assert typeid >= 0
        if self.is_varsize(typeid):
            return llmemory.ItemOffset(self.types[typeid])
        else:
            return 0

    def varsize_offset_to_variable_part(self, typeid):
        assert typeid >= 0
        if self.is_varsize(typeid):
            return llmemory.ArrayItemsOffset(self.types[typeid])
        else:
            return 0

    def varsize_offset_to_length(self, typeid):
        assert typeid >= 0
        if self.is_varsize(typeid):
            TYPE = self.types[typeid]
            if isinstance(TYPE, lltype.Array):
                return 0
            else:
                return llmemory.FieldOffset(TYPE, TYPE._arrayfld)
        else:
            return 0

    def varsize_offsets_to_gcpointers_in_var_part(self, typeid):
        assert typeid >= 0
        if self.is_varsize(typeid):
            return lltypelayout.varsize_offsets_to_gcpointers_in_var_part(
                self.types[typeid])
        else:
            return 0
    
def getfunctionptr(annotator, graphfunc):
    """Make a functionptr from the given Python function."""
    graph = annotator.bookkeeper.getdesc(graphfunc).cachedgraph(None)
    llinputs = [v.concretetype for v in graph.getargs()]
    lloutput = graph.getreturnvar().concretetype
    FT = lltype.FuncType(llinputs, lloutput)
    _callable = graphfunc
    return lltypesimulation.functionptr(FT, graphfunc.func_name,
                                        graph=graph, _callable=_callable)


class GcWrapper(object):
    def __init__(self, llinterp, flowgraphs, gc_class):
        self.query_types = QueryTypes()
        # XXX there might me GCs that have headers that depend on the type
        # therefore we have to change the query functions to annotatable ones
        # later
        self.gc = gc_class()
        self.gc.set_query_functions(*self.query_types.get_setup_query_functions())
        fgcc = FlowGraphConstantConverter(flowgraphs, self.gc, self.query_types)
        fgcc.convert()
        self.gc.set_query_functions(*self.query_types.create_query_functions())
        self.llinterp = llinterp
        self.gc.get_roots = self.get_roots
        self.constantroots = fgcc.cvter.constantroots
        self.pseudo_root_pointers = NULL
        self.roots = []


    def get_arg_malloc(self, TYPE, size=0):
        typeid = self.query_types.get_typeid(TYPE)
        return [typeid, size]

    def get_funcptr_malloc(self):
        return self.llinterp.heap.functionptr(gc.gc_interface["malloc"], "malloc",
                                             _callable=self.gc.malloc)

    def adjust_result_malloc(self, address, TYPE, size=0):
        result = lltypesimulation.init_object_on_address(address, TYPE, size)
        self.update_changed_addresses()
        return result


    def needs_write_barrier(self, TYPE):
        return (hasattr(self.gc, "write_barrier") and
                isinstance(TYPE, lltype.Ptr) and
                isinstance(TYPE.TO, (lltype.GcStruct, lltype.GcArray)))

    def get_arg_write_barrier(self, obj, index_or_field, item):
        #XXX: quick hack to get the correct addresses, fix later
        layout = lltypelayout.get_layout(lltype.typeOf(obj).TO)
        if isinstance(lltype.typeOf(obj).TO, lltype.Array):
            assert isinstance(index_or_field, int)
            offset = layout[0] + layout[1] * index_or_field
            addr_to = obj._address + layout[0] + index_or_field * layout[1]
            return item._address, addr_to, obj._address
        else:
            offset = layout[index_or_field]
            addr_to = obj._address + offset
            return item._address, addr_to, obj._address
            

    def get_funcptr_write_barrier(self):
        return self.llinterp.heap.functionptr(gc.gc_interface["write_barrier"],
                                             "write_barrier",
                                             _callable=self.gc.write_barrier)
 

    def update_changed_addresses(self):
        for i, root in enumerate(self.roots):
            root.__dict__['_address'] = self.pseudo_root_pointers.address[i]

    def get_roots_from_llinterp(self):
        if self.pseudo_root_pointers != NULL:
            raw_free(self.pseudo_root_pointers)
        roots = [r for r in self.llinterp.find_roots()
                     if isinstance(r._TYPE.TO,
                                   (lltype.GcStruct, lltype.GcArray))]
        self.roots = roots + self.constantroots
        self.roots = [r for r in self.roots
                          if isinstance(r._TYPE.TO,
                                        (lltype.Struct, lltype.Array))]
        if len(self.roots) == 0:
            self.pseudo_root_pointers = NULL
        else:
            self.pseudo_root_pointers = raw_malloc(len(self.roots) * INT_SIZE)
        return self.roots

    def get_roots(self):
        self.get_roots_from_llinterp()
        ll = AddressLinkedList()
        for i, root in enumerate(self.roots):
            self.pseudo_root_pointers.address[i] = root._address
            ll.append(self.pseudo_root_pointers + INT_SIZE * i)
        return ll

class AnnotatingGcWrapper(GcWrapper):
    def __init__(self, llinterp, flowgraphs, gc_class):
        super(AnnotatingGcWrapper, self).__init__(llinterp, flowgraphs, gc_class)
        # tell the real-built gc to free its memory as it is only used for
        # initialisation
        self.gc.free_memory()
        self.annotate_rtype_gc()

    def annotate_rtype_gc(self):
        # annotate and specialize functions
        gc_class = self.gc.__class__
        def instantiate_linked_list():
            return AddressLinkedList()
        f1, f2, f3, f4, f5, f6, f7 = self.query_types.create_query_functions()
        def instantiate_gc():
            gc = gc_class()
            gc.set_query_functions(f1, f2, f3, f4, f5, f6, f7)
            return gc
        func = gc.get_dummy_annotate(self.gc.__class__)
        self.gc.get_roots = gc.dummy_get_roots1
        a = RPythonAnnotator()
        a.build_types(instantiate_gc, [])
        a.build_types(func, [])
        a.build_types(instantiate_linked_list, [])
        typer = RPythonTyper(a)
        typer.specialize()
        self.annotator = a
        
        # convert constants
        fgcc = FlowGraphConstantConverter(a.translator.graphs)
        fgcc.convert()
        self.malloc_graph = a.bookkeeper.getdesc(self.gc.malloc.im_func).cachedgraph(None)
        self.write_barrier_graph = a.bookkeeper.getdesc(self.gc.write_barrier.im_func).cachedgraph(None)

        # create a gc via invoking instantiate_gc
        self.gcptr = self.llinterp.eval_graph(
            a.bookkeeper.getdesc(instantiate_gc).cachedgraph(None))
        GETROOTS_FUNCTYPE = lltype.typeOf(
            getfunctionptr(a, gc.dummy_get_roots1)).TO
        setattr(self.gcptr, "inst_get_roots",
                lltypesimulation.functionptr(GETROOTS_FUNCTYPE, "get_roots",
                                             _callable=self.get_roots))
        #get funcptrs neccessary to build the result of get_roots
        self.instantiate_linked_list = getfunctionptr(
            a, instantiate_linked_list)
        self.append_linked_list = getfunctionptr(
            a, AddressLinkedList.append.im_func)
        self.pop_linked_list = getfunctionptr(
            a, AddressLinkedList.pop.im_func)
        self.gc.get_roots = None
        self.translator = a.translator
##         a.translator.view()

    def get_arg_malloc(self, TYPE, size=0):
        typeid = self.query_types.get_typeid(TYPE)
        return [self.gcptr, typeid, size]

    def get_funcptr_malloc(self):
        return self.llinterp.heap.functionptr(gc.gc_interface["malloc"], "malloc",
                                             _callable=self.gc.malloc,
                                             graph=self.malloc_graph)

    def adjust_result_malloc(self, address, TYPE, size=0):
        result = lltypesimulation.init_object_on_address(address, TYPE, size)
        self.update_changed_addresses()
        return result

    def get_arg_write_barrier(self, obj, index_or_field, item):
        #XXX: quick hack to get the correct addresses, fix later
        layout = lltypelayout.get_layout(lltype.typeOf(obj).TO)
        if isinstance(lltype.typeOf(obj).TO, lltype.Array):
            assert isinstance(index_or_field, int)
            offset = layout[0] + layout[1] * index_or_field
            addr_to = obj._address + layout[0] + index_or_field * layout[1]
            return self.gcptr, item._address, addr_to, obj._address
        else:
            offset = layout[index_or_field]
            addr_to = obj._address + offset
            return self.gcptr, item._address, addr_to, obj._address
            
    def get_funcptr_write_barrier(self):
        return self.llinterp.heap.functionptr(gc.gc_interface["write_barrier"],
                                             "write_barrier",
                                             _callable=self.gc.write_barrier,
                                             graph=self.write_barrier_graph)


    def get_roots(self):
        # call the llinterpreter to construct the result in a suitable way
        self.get_roots_from_llinterp()
        ll = self.llinterp.active_frame.op_direct_call(
            self.instantiate_linked_list)
        for i, root in enumerate(self.roots):
            self.pseudo_root_pointers.address[i] = root._address
            self.llinterp.active_frame.op_direct_call(
                self.append_linked_list, ll,
                self.pseudo_root_pointers + INT_SIZE * i)
        return ll
