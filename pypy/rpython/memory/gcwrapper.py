from pypy.rpython.lltypesystem import lltype, llmemory, llheap
from pypy.rpython import llinterp
from pypy.rpython.memory.support import get_address_linked_list
from pypy.rpython.memory import gctypelayout
from pypy.objspace.flow.model import Constant


class GCManagedHeap(object):

    def __init__(self, llinterp, flowgraphs, gc_class, GC_PARAMS={}):
        self.AddressLinkedList = get_address_linked_list(10)
        self.gc = gc_class(self.AddressLinkedList, **GC_PARAMS)
        self.gc.get_roots = self.get_roots_from_llinterp
        self.llinterp = llinterp
        self.prepare_graphs(flowgraphs)
        self.gc.setup()

    def prepare_graphs(self, flowgraphs):
        layoutbuilder = DirectRunLayoutBuilder(self.llinterp)
        self.get_type_id = layoutbuilder.get_type_id
        self.gc.set_query_functions(*layoutbuilder.get_query_functions())

        constants = collect_constants(flowgraphs)
        for obj in constants:
            TYPE = lltype.typeOf(obj)
            layoutbuilder.consider_constant(TYPE, obj, self.gc)

        self.constantroots = layoutbuilder.addresses_of_static_ptrs
        self.constantrootsnongc = layoutbuilder.addresses_of_static_ptrs_in_nongc

    def get_roots_from_llinterp(self, with_static=True):
        sizeofaddr = llmemory.sizeof(llmemory.Address)
        ll = [llmemory.NULL]     # end marker
        if with_static:
            for addrofaddr in self.constantroots:
                if addrofaddr.address[0]:
                    ll.append(addrofaddr)
        for addrofaddr in self.constantrootsnongc:
            if addrofaddr.address[0]:
                ll.append(addrofaddr)
        for addrofaddr in self.llinterp.find_roots():
            if addrofaddr.address[0]:
                ll.append(addrofaddr)
        return RootLinkedList(ll)

    # ____________________________________________________________
    #
    # Interface for the llinterp
    #
    def malloc(self, TYPE, n=None, flavor='gc', zero=False):
        if flavor == 'gc':
            typeid = self.get_type_id(TYPE)
            addr = self.gc.malloc(typeid, n, zero=zero)
            return llmemory.cast_adr_to_ptr(addr, lltype.Ptr(TYPE))
        else:
            return lltype.malloc(TYPE, n, flavor=flavor, zero=zero)

    def free(self, TYPE, flavor='gc'):
        assert flavor != 'gc'
        return lltype.free(TYPE, flavor=flavor)

    def setfield(self, obj, fieldname, fieldvalue):
        STRUCT = lltype.typeOf(obj).TO
        addr = llmemory.cast_ptr_to_adr(obj)
        addr += llmemory.offsetof(STRUCT, fieldname)
        self.setinterior(obj, addr, getattr(STRUCT, fieldname), fieldvalue)

    def setarrayitem(self, array, index, newitem):
        ARRAY = lltype.typeOf(array).TO
        addr = llmemory.cast_ptr_to_adr(array)
        addr += llmemory.itemoffsetof(ARRAY, index)
        self.setinterior(array, addr, ARRAY.OF, newitem)

    def setinterior(self, toplevelcontainer, inneraddr, INNERTYPE, newvalue):
        if isinstance(INNERTYPE, lltype.Ptr) and INNERTYPE.TO._gckind == 'gc':
            self.gc.write_barrier(llmemory.cast_ptr_to_adr(newvalue),
                                  inneraddr,
                                  llmemory.cast_ptr_to_adr(toplevelcontainer))
        else:
            llheap.setinterior(toplevelcontainer, inneraddr,
                               INNERTYPE, newvalue)

    def collect(self):
        self.gc.collect()

    def weakref_create(self, obj):
        type_id = self.get_type_id(gctypelayout.WEAKREF)
        addr = self.gc.malloc(type_id, None, zero=False)
        result = llmemory.cast_adr_to_ptr(addr, gctypelayout.WEAKREFPTR)
        result.weakptr = llmemory.cast_ptr_to_adr(obj)
        return llmemory.cast_ptr_to_weakrefptr(result)
    
    def weakref_deref(self, PTRTYPE, obj):
        addr = gctypelayout.ll_weakref_deref(obj)
        return llmemory.cast_adr_to_ptr(addr, PTRTYPE)

    def gc_id(self, ptr):
        ptr = lltype.cast_opaque_ptr(llmemory.GCREF, ptr)
        return self.gc.id(ptr)

    # ____________________________________________________________

class RootLinkedList(object):
    _alloc_flavor_ = 'raw'

    def __init__(self, lst):
        self._lst = lst
        self.pop = lst.pop


class DirectRunLayoutBuilder(gctypelayout.TypeLayoutBuilder):

    def __init__(self, llinterp):
        self.llinterp = llinterp
        super(DirectRunLayoutBuilder, self).__init__()

    def make_finalizer_funcptr_for_type(self, TYPE):
        from pypy.rpython.memory.gctransform.support import get_rtti, \
                type_contains_pyobjs
        rtti = get_rtti(TYPE)
        if rtti is not None and hasattr(rtti._obj, 'destructor_funcptr'):
            destrptr = rtti._obj.destructor_funcptr
            DESTR_ARG = lltype.typeOf(destrptr).TO.ARGS[0]
            destrgraph = destrptr._obj.graph
        else:
            return None

        assert not type_contains_pyobjs(TYPE), "not implemented"
        def ll_finalizer(addr):
            try:
                v = llmemory.cast_adr_to_ptr(addr, DESTR_ARG)
                self.llinterp.eval_graph(destrgraph, [v], recursive=True)
            except llinterp.LLException:
                raise RuntimeError(
                    "a finalizer raised an exception, shouldn't happen")
        return ll_finalizer


def collect_constants(graphs):
    constants = {}
    def collect_args(args):
        for arg in args:
            if (isinstance(arg, Constant) and
                arg.concretetype is not lltype.Void):
                reccollect(constants, arg.value)
    for graph in graphs:
        for block in graph.iterblocks():
            collect_args(block.inputargs)
            for op in block.operations:
                collect_args(op.args)
        for link in graph.iterlinks():
            collect_args(link.args)
            if hasattr(link, "llexitcase"):
                reccollect(constants, link.llexitcase)
    return constants

def reccollect(constants, llvalue):
    T = lltype.typeOf(llvalue)
    if isinstance(T, lltype.Ptr) and llvalue and llvalue._obj not in constants:
        constants[llvalue._obj] = True
        TYPE = T.TO
        if isinstance(TYPE, lltype.Struct):
            for name in TYPE._names:
                reccollect(constants, getattr(llvalue, name))
        elif isinstance(TYPE, lltype.Array):
            for llitem in llvalue:
                reccollect(constants, llitem)
        parent, parentindex = lltype.parentlink(llvalue._obj)
        if parent is not None:
            reccollect(constants, parent._as_ptr())

def prepare_graphs_and_create_gc(llinterp, GCClass, GC_PARAMS={}):
    flowgraphs = llinterp.typer.annotator.translator.graphs[:]
    llinterp.heap = GCManagedHeap(llinterp, flowgraphs, GCClass, GC_PARAMS)
