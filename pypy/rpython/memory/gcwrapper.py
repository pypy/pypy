from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.memory.support import get_address_linked_list
from pypy.rpython.memory import gctypelayout
from pypy.objspace.flow.model import Constant


class GCManagedHeap(object):

    def __init__(self, llinterp, flowgraphs, gc_class):
        self.AddressLinkedList = get_address_linked_list(10, hackishpop=True)
        self.gc = gc_class(self.AddressLinkedList)
        self.gc.get_roots = self.get_roots_from_llinterp
        self.llinterp = llinterp
        self.constantroots = []
        self.prepare_graphs(flowgraphs)
        self.gc.setup()

    def prepare_graphs(self, flowgraphs):
        layoutbuilder = DirectRunLayoutBuilder()
        self.get_type_id = layoutbuilder.get_type_id
        self.gc.set_query_functions(*layoutbuilder.get_query_functions())

        constants = collect_constants(flowgraphs)
        for obj in constants:
            TYPE = lltype.typeOf(obj)
            layoutbuilder.consider_constant(TYPE, obj, self.gc)

        sizeofaddr = llmemory.sizeof(llmemory.Address)
        for addr in layoutbuilder.static_gc_roots:
            addrofaddr = llmemory.raw_malloc(sizeofaddr)
            addrofaddr.address[0] = addr
            self.constantroots.append(addrofaddr)
        self.constantroots += layoutbuilder.addresses_of_static_ptrs_in_nongc

    def get_roots_from_llinterp(self):
        sizeofaddr = llmemory.sizeof(llmemory.Address)
        ll = self.AddressLinkedList()
        for addrofaddr in self.constantroots:
            ll.append(addrofaddr)
        for addrofaddr in self.llinterp.find_roots():
            ll.append(addrofaddr)
        return ll

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

    def setfield(self, obj, fieldname, fieldvalue):
        # XXX use write_barrier - but we need the address of the GcStruct
        setattr(obj, fieldname, fieldvalue)

    def setarrayitem(self, array, index, newitem):
        # XXX use write_barrier - but we need the address of the GcStruct
        array[index] = newitem

    # ____________________________________________________________


class DirectRunLayoutBuilder(gctypelayout.TypeLayoutBuilder):

    def make_finalizer_funcptr_for_type(self, TYPE):
        return None     # XXX


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

def prepare_graphs_and_create_gc(llinterp, GCClass):
    flowgraphs = llinterp.typer.annotator.translator.graphs[:]
    llinterp.heap = GCManagedHeap(llinterp, flowgraphs, GCClass)
