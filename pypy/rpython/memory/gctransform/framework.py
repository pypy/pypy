from pypy.rpython.memory.gctransform.transform import GCTransformer, var_ispyobj
from pypy.rpython.memory.gctransform.support import find_gc_ptrs_in_type, \
     get_rtti, ll_call_destructor, type_contains_pyobjs
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython import rmodel
from pypy.rpython.memory import gc, lladdress
from pypy.rpython.memory.gcheader import GCHeaderBuilder
from pypy.rlib.rarithmetic import ovfcheck
from pypy.rlib.objectmodel import debug_assert
from pypy.translator.backendopt import graphanalyze
from pypy.annotation import model as annmodel
from pypy.rpython import annlowlevel
from pypy.rpython.rbuiltin import gen_cast
import sys


class CollectAnalyzer(graphanalyze.GraphAnalyzer):
    def operation_is_true(self, op):
        if op.opname in ('gc__collect', 'gc_x_become'):
            return True
        if op.opname in ('malloc', 'malloc_varsize'):
            flags = op.args[1].value
            return flags['flavor'] == 'gc' and not flags.get('nocollect', False)

ADDRESS_VOID_FUNC = lltype.FuncType([llmemory.Address], lltype.Void)

class FrameworkGCTransformer(GCTransformer):
    use_stackless = False
    extra_static_slots = 0
    finished_tables = False
    root_stack_depth = 163840

    from pypy.rpython.memory.gc import MarkSweepGC as GCClass
    GC_PARAMS = {'start_heap_size': 8*1024*1024} # XXX adjust

    def __init__(self, translator):
        from pypy.rpython.memory.support import get_address_linked_list
        super(FrameworkGCTransformer, self).__init__(translator, inline=True)
        AddressLinkedList = get_address_linked_list()
        GCClass = self.GCClass
        self.finalizer_funcptrs = {}
        self.FINALIZERTYPE = lltype.Ptr(ADDRESS_VOID_FUNC)
        class GCData(object):
            # types of the GC information tables
            OFFSETS_TO_GC_PTR = lltype.Array(lltype.Signed)
            TYPE_INFO = lltype.Struct("type_info",
                ("isvarsize",   lltype.Bool),
                ("finalyzer",   self.FINALIZERTYPE),
                ("fixedsize",   lltype.Signed),
                ("ofstoptrs",   lltype.Ptr(OFFSETS_TO_GC_PTR)),
                ("varitemsize", lltype.Signed),
                ("ofstovar",    lltype.Signed),
                ("ofstolength", lltype.Signed),
                ("varofstoptrs",lltype.Ptr(OFFSETS_TO_GC_PTR)),
                ("weakptrofs",  lltype.Signed),
                )
            TYPE_INFO_TABLE = lltype.Array(TYPE_INFO)

        def q_is_varsize(typeid):
            return gcdata.type_info_table[typeid].isvarsize

        def q_finalyzer(typeid):
            return gcdata.type_info_table[typeid].finalyzer

        def q_offsets_to_gc_pointers(typeid):
            return gcdata.type_info_table[typeid].ofstoptrs

        def q_fixed_size(typeid):
            return gcdata.type_info_table[typeid].fixedsize

        def q_varsize_item_sizes(typeid):
            return gcdata.type_info_table[typeid].varitemsize

        def q_varsize_offset_to_variable_part(typeid):
            return gcdata.type_info_table[typeid].ofstovar

        def q_varsize_offset_to_length(typeid):
            return gcdata.type_info_table[typeid].ofstolength

        def q_varsize_offsets_to_gcpointers_in_var_part(typeid):
            return gcdata.type_info_table[typeid].varofstoptrs

        def q_weakpointer_offset(typeid):
            return gcdata.type_info_table[typeid].weakptrofs

        gcdata = GCData()
        # set up dummy a table, to be overwritten with the real one in finish()
        gcdata.type_info_table = lltype.malloc(GCData.TYPE_INFO_TABLE, 0,
                                               immortal=True)
        gcdata.static_roots = lltype.malloc(lltype.Array(llmemory.Address), 0,
                                            immortal=True)
        # initialize the following two fields with a random non-NULL address,
        # to make the annotator happy.  The fields are patched in finish()
        # to point to a real array (not 'static_roots', another one).
        a_random_address = llmemory.cast_ptr_to_adr(gcdata.type_info_table)
        gcdata.static_root_start = a_random_address   # patched in finish()
        gcdata.static_root_end = a_random_address     # patched in finish()
        self.gcdata = gcdata
        self.type_info_list = []
        self.id_of_type = {}      # {LLTYPE: type_id}
        self.seen_roots = {}
        self.static_gc_roots = []
        self.addresses_of_static_ptrs_in_nongc = []
        self.offsettable_cache = {}
        self.malloc_fnptr_cache = {}

        sizeofaddr = llmemory.sizeof(llmemory.Address)

        StackRootIterator = self.build_stack_root_iterator()
        gcdata.gc = GCClass(AddressLinkedList, get_roots=StackRootIterator, **self.GC_PARAMS)

        def frameworkgc_setup():
            # run-time initialization code
            StackRootIterator.setup_root_stack()
            gcdata.gc.setup()
            gcdata.gc.set_query_functions(
                q_is_varsize,
                q_finalyzer,
                q_offsets_to_gc_pointers,
                q_fixed_size,
                q_varsize_item_sizes,
                q_varsize_offset_to_variable_part,
                q_varsize_offset_to_length,
                q_varsize_offsets_to_gcpointers_in_var_part,
                q_weakpointer_offset)

        bk = self.translator.annotator.bookkeeper

        # the point of this little dance is to not annotate
        # self.gcdata.type_info_table as a constant.
        data_classdef = bk.getuniqueclassdef(GCData)
        data_classdef.generalize_attr(
            'type_info_table',
            annmodel.SomePtr(lltype.Ptr(GCData.TYPE_INFO_TABLE)))
        data_classdef.generalize_attr(
            'static_roots',
            annmodel.SomePtr(lltype.Ptr(lltype.Array(llmemory.Address))))
        data_classdef.generalize_attr(
            'static_root_start',
            annmodel.SomeAddress())
        data_classdef.generalize_attr(
            'static_root_end',
            annmodel.SomeAddress())

        annhelper = annlowlevel.MixLevelHelperAnnotator(self.translator.rtyper)

        def getfn(ll_function, args_s, s_result, inline=False,
                  minimal_transform=True):
            graph = annhelper.getgraph(ll_function, args_s, s_result)
            if minimal_transform:
                self.need_minimal_transform(graph)
            if inline:
                self.graphs_to_inline[graph] = True
            return annhelper.graph2const(graph)

        self.frameworkgc_setup_ptr = getfn(frameworkgc_setup, [],
                                           annmodel.s_None)
        if StackRootIterator.need_root_stack:
            self.pop_root_ptr = getfn(StackRootIterator.pop_root, [],
                                      annmodel.s_None,
                                      inline = True)
            self.push_root_ptr = getfn(StackRootIterator.push_root,
                                       [annmodel.SomeAddress()],
                                       annmodel.s_None,
                                       inline = True)
            self.incr_stack_ptr = getfn(StackRootIterator.incr_stack,
                                       [annmodel.SomeInteger()],
                                       annmodel.SomeAddress(),
                                       inline = True)
            self.decr_stack_ptr = getfn(StackRootIterator.decr_stack,
                                       [annmodel.SomeInteger()],
                                       annmodel.s_None,
                                       inline = True)
            self.save_addr_ptr = getfn(StackRootIterator.save_addr,
                                       [annmodel.SomeAddress(),
                                        annmodel.SomeInteger(),
                                        annmodel.SomeAddress()],
                                       annmodel.s_None,
                                       inline = True)
        else:
            self.push_root_ptr = None
            self.pop_root_ptr = None
            self.incr_stack_ptr = None
            self.decr_stack_ptr = None
            self.save_addr_ptr = None
        self.weakref_deref_ptr = self.inittime_helper(
            ll_weakref_deref, [llmemory.WeakRefPtr], llmemory.Address)
        
        classdef = bk.getuniqueclassdef(GCClass)
        s_gc = annmodel.SomeInstance(classdef)
        s_gcref = annmodel.SomePtr(llmemory.GCREF)
        self.malloc_fixedsize_ptr = getfn(
            GCClass.malloc_fixedsize.im_func,
            [s_gc, annmodel.SomeInteger(nonneg=True),
             annmodel.SomeInteger(nonneg=True),
             annmodel.SomeBool(), annmodel.SomeBool(),
             annmodel.SomeBool()], s_gcref,
            inline = False)
        self.malloc_fixedsize_clear_ptr = getfn(
            GCClass.malloc_fixedsize_clear.im_func,
            [s_gc, annmodel.SomeInteger(nonneg=True),
             annmodel.SomeInteger(nonneg=True),
             annmodel.SomeBool(), annmodel.SomeBool(),
             annmodel.SomeBool()], s_gcref,
            inline = False)
##         self.malloc_varsize_ptr = getfn(
##             GCClass.malloc_varsize.im_func,
##             [s_gc] + [annmodel.SomeInteger(nonneg=True) for i in range(5)]
##             + [annmodel.SomeBool(), annmodel.SomeBool()], s_gcref)
        self.malloc_varsize_clear_ptr = getfn(
            GCClass.malloc_varsize_clear.im_func,
            [s_gc] + [annmodel.SomeInteger(nonneg=True) for i in range(5)]
            + [annmodel.SomeBool(), annmodel.SomeBool()], s_gcref)
        self.collect_ptr = getfn(GCClass.collect.im_func,
            [s_gc], annmodel.s_None)

        self.statistics_ptr = getfn(GCClass.statistics.im_func,
                                    [s_gc, annmodel.SomeInteger()],
                                    annmodel.SomeInteger())

        # experimental gc_x_* operations
        s_x_pool  = annmodel.SomePtr(gc.X_POOL_PTR)
        s_x_clone = annmodel.SomePtr(gc.X_CLONE_PTR)
        # the x_*() methods use some regular mallocs that must be
        # transformed in the normal way
        self.x_swap_pool_ptr = getfn(GCClass.x_swap_pool.im_func,
                                     [s_gc, s_x_pool],
                                     s_x_pool,
                                     minimal_transform = False)
        self.x_clone_ptr = getfn(GCClass.x_clone.im_func,
                                 [s_gc, s_x_clone],
                                 annmodel.s_None,
                                 minimal_transform = False)

        self.x_become_ptr = getfn(
            GCClass.x_become.im_func,
            [s_gc, annmodel.SomeAddress(), annmodel.SomeAddress()],
            annmodel.s_None)

        annhelper.finish()   # at this point, annotate all mix-level helpers
        annhelper.backend_optimize()

        self.collect_analyzer = CollectAnalyzer(self.translator)
        self.collect_analyzer.analyze_all()

        s_gc = self.translator.annotator.bookkeeper.valueoftype(GCClass)
        r_gc = self.translator.rtyper.getrepr(s_gc)
        self.c_const_gc = rmodel.inputconst(r_gc, self.gcdata.gc)

        HDR = self._gc_HDR = self.gcdata.gc.gcheaderbuilder.HDR
        self._gc_fields = fields = []
        for fldname in HDR._names:
            FLDTYPE = getattr(HDR, fldname)
            fields.append(('_' + fldname, FLDTYPE))

    def build_stack_root_iterator(self):
        gcdata = self.gcdata
        sizeofaddr = llmemory.sizeof(llmemory.Address)
        rootstacksize = sizeofaddr * self.root_stack_depth

        class StackRootIterator:
            _alloc_flavor_ = 'raw'
            def setup_root_stack():
                stackbase = lladdress.raw_malloc(rootstacksize)
                debug_assert(bool(stackbase), "could not allocate root stack")
                lladdress.raw_memclear(stackbase, rootstacksize)
                gcdata.root_stack_top  = stackbase
                gcdata.root_stack_base = stackbase
                i = 0
                while i < len(gcdata.static_roots):
                    StackRootIterator.push_root(gcdata.static_roots[i])
                    i += 1
            setup_root_stack = staticmethod(setup_root_stack)

            need_root_stack = True
            
            def incr_stack(n):
                top = gcdata.root_stack_top
                gcdata.root_stack_top = top + n*sizeofaddr
                return top
            incr_stack = staticmethod(incr_stack)
            
            def save_addr(top, k, addr):
                top.address[k] = addr
            save_addr = staticmethod(save_addr)
            
            def decr_stack(n):
                gcdata.root_stack_top -= n*sizeofaddr
            decr_stack = staticmethod(decr_stack)
                
            def push_root(addr):
                top = gcdata.root_stack_top
                top.address[0] = addr
                gcdata.root_stack_top = top + sizeofaddr
            push_root = staticmethod(push_root)

            def pop_root():
                gcdata.root_stack_top -= sizeofaddr
            pop_root = staticmethod(pop_root)

            def __init__(self):
                self.stack_current = gcdata.root_stack_top
                self.static_current = gcdata.static_root_start

            def pop(self):
                while self.static_current != gcdata.static_root_end:
                    result = self.static_current
                    self.static_current += sizeofaddr
                    if result.address[0].address[0] != llmemory.NULL:
                        return result.address[0]
                while self.stack_current != gcdata.root_stack_base:
                    self.stack_current -= sizeofaddr
                    if self.stack_current.address[0] != llmemory.NULL:
                        return self.stack_current
                return llmemory.NULL

        return StackRootIterator

    def get_type_id(self, TYPE):
        try:
            return self.id_of_type[TYPE]
        except KeyError:
            assert not self.finished_tables
            assert isinstance(TYPE, (lltype.GcStruct, lltype.GcArray))
            # Record the new type_id description as a small dict for now.
            # It will be turned into a Struct("type_info") in finish()
            type_id = len(self.type_info_list)
            info = {}
            self.type_info_list.append(info)
            self.id_of_type[TYPE] = type_id
            offsets = offsets_to_gc_pointers(TYPE)
            info["ofstoptrs"] = self.offsets2table(offsets, TYPE)
            info["finalyzer"] = self.finalizer_funcptr_for_type(TYPE)
            info["weakptrofs"] = weakpointer_offset(TYPE)
            if not TYPE._is_varsize():
                info["isvarsize"] = False
                info["fixedsize"] = llmemory.sizeof(TYPE)
                info["ofstolength"] = -1
            else:
                info["isvarsize"] = True
                info["fixedsize"] = llmemory.sizeof(TYPE, 0)
                if isinstance(TYPE, lltype.Struct):
                    ARRAY = TYPE._flds[TYPE._arrayfld]
                    ofs1 = llmemory.offsetof(TYPE, TYPE._arrayfld)
                    info["ofstolength"] = ofs1 + llmemory.ArrayLengthOffset(ARRAY)
                    if ARRAY.OF != lltype.Void:
                        info["ofstovar"] = ofs1 + llmemory.itemoffsetof(ARRAY, 0)
                    else:
                        info["fixedsize"] = ofs1 + llmemory.sizeof(lltype.Signed)
                    if ARRAY._hints.get('isrpystring'):
                        info["fixedsize"] = llmemory.sizeof(TYPE, 1)
                else:
                    ARRAY = TYPE
                    info["ofstolength"] = llmemory.ArrayLengthOffset(ARRAY)
                    if ARRAY.OF != lltype.Void:
                        info["ofstovar"] = llmemory.itemoffsetof(TYPE, 0)
                    else:
                        info["fixedsize"] = llmemory.ArrayLengthOffset(ARRAY) + llmemory.sizeof(lltype.Signed)
                assert isinstance(ARRAY, lltype.Array)
                if ARRAY.OF != lltype.Void:
                    offsets = offsets_to_gc_pointers(ARRAY.OF)
                    info["varofstoptrs"] = self.offsets2table(offsets, ARRAY.OF)
                    info["varitemsize"] = llmemory.sizeof(ARRAY.OF)
                else:
                    info["varofstoptrs"] = self.offsets2table((), lltype.Void)
                    info["varitemsize"] = llmemory.sizeof(ARRAY.OF)
            return type_id

    def finalizer_funcptr_for_type(self, TYPE):
        if TYPE in self.finalizer_funcptrs:
            return self.finalizer_funcptrs[TYPE]

        rtti = get_rtti(TYPE)
        if rtti is not None and hasattr(rtti._obj, 'destructor_funcptr'):
            destrptr = rtti._obj.destructor_funcptr
            DESTR_ARG = lltype.typeOf(destrptr).TO.ARGS[0]
        else:
            destrptr = None
            DESTR_ARG = None

        assert not type_contains_pyobjs(TYPE), "not implemented"
        if destrptr:
            def ll_finalizer(addr):
                v = llmemory.cast_adr_to_ptr(addr, DESTR_ARG)
                ll_call_destructor(destrptr, v)
            fptr = self.annotate_helper(ll_finalizer, [llmemory.Address], lltype.Void)
        else:
            fptr = lltype.nullptr(ADDRESS_VOID_FUNC)

        self.finalizer_funcptrs[TYPE] = fptr
        return fptr

    def consider_constant(self, TYPE, value):
        if value is not lltype.top_container(value):
            return
        if id(value) in self.seen_roots:
            return
        self.seen_roots[id(value)] = True

        if isinstance(TYPE, (lltype.GcStruct, lltype.GcArray)):
            typeid = self.get_type_id(TYPE)
            hdrbuilder = self.gcdata.gc.gcheaderbuilder
            hdr = hdrbuilder.new_header(value)
            adr = llmemory.cast_ptr_to_adr(hdr)
            self.gcdata.gc.init_gc_object(adr, typeid)

        if find_gc_ptrs_in_type(TYPE):
            adr = llmemory.cast_ptr_to_adr(value._as_ptr())
            if isinstance(TYPE, (lltype.GcStruct, lltype.GcArray)):
                self.static_gc_roots.append(adr)
            else:
                for a in gc_pointers_inside(value, adr):
                    self.addresses_of_static_ptrs_in_nongc.append(a)

    def gc_fields(self):
        return self._gc_fields

    def gc_field_values_for(self, obj):
        hdr = self.gcdata.gc.gcheaderbuilder.header_of_object(obj)
        HDR = self._gc_HDR
        return [getattr(hdr, fldname) for fldname in HDR._names]

    def offsets2table(self, offsets, TYPE):
        try:
            return self.offsettable_cache[TYPE]
        except KeyError:
            cachedarray = lltype.malloc(self.gcdata.OFFSETS_TO_GC_PTR,
                                        len(offsets), immortal=True)
            for i, value in enumerate(offsets):
                cachedarray[i] = value
            self.offsettable_cache[TYPE] = cachedarray
            return cachedarray

    def finish_tables(self):
        self.finished_tables = True
        table = lltype.malloc(self.gcdata.TYPE_INFO_TABLE,
                              len(self.type_info_list), immortal=True)
        for tableentry, newcontent in zip(table, self.type_info_list):
            for key, value in newcontent.items():
                setattr(tableentry, key, value)
        self.offsettable_cache = None

        # replace the type_info_table pointer in gcdata -- at this point,
        # the database is in principle complete, so it has already seen
        # the old (empty) array.  We need to force it to consider the new
        # array now.  It's a bit hackish as the old empty array will also
        # be generated in the C source, but that's a rather minor problem.

        # XXX because we call inputconst already in replace_malloc, we can't
        # modify the instance, we have to modify the 'rtyped instance'
        # instead.  horrors.  is there a better way?

        s_gcdata = self.translator.annotator.bookkeeper.immutablevalue(
            self.gcdata)
        r_gcdata = self.translator.rtyper.getrepr(s_gcdata)
        ll_instance = rmodel.inputconst(r_gcdata, self.gcdata).value
        ll_instance.inst_type_info_table = table
        #self.gcdata.type_info_table = table

        ll_static_roots = lltype.malloc(lltype.Array(llmemory.Address),
                                        len(self.static_gc_roots) +
                                            self.extra_static_slots,
                                        immortal=True)
        for i in range(len(self.static_gc_roots)):
            adr = self.static_gc_roots[i]
            ll_static_roots[i] = adr
        ll_instance.inst_static_roots = ll_static_roots

        ll_static_roots_inside = lltype.malloc(lltype.Array(llmemory.Address),
                                               len(self.addresses_of_static_ptrs_in_nongc),
                                               immortal=True)
        for i in range(len(self.addresses_of_static_ptrs_in_nongc)):
            ll_static_roots_inside[i] = self.addresses_of_static_ptrs_in_nongc[i]
        ll_instance.inst_static_root_start = llmemory.cast_ptr_to_adr(ll_static_roots_inside) + llmemory.ArrayItemsOffset(lltype.Array(llmemory.Address))
        ll_instance.inst_static_root_end = ll_instance.inst_static_root_start + llmemory.sizeof(llmemory.Address) * len(ll_static_roots_inside)

        newgcdependencies = []
        newgcdependencies.append(table)
        newgcdependencies.append(ll_static_roots)
        newgcdependencies.append(ll_static_roots_inside)
        return newgcdependencies

    def gct_direct_call(self, hop):
        if self.collect_analyzer.analyze(hop.spaceop):
            self.push_roots(hop)
            self.default(hop)
            self.pop_roots(hop)
        else:
            self.default(hop)

    gct_indirect_call = gct_direct_call

    def gct_fv_gc_malloc(self, hop, flags, TYPE, *args):
        op = hop.spaceop
        flavor = flags['flavor']
        c_can_collect = rmodel.inputconst(lltype.Bool, not flags.get('nocollect', False))

        PTRTYPE = op.result.concretetype
        assert PTRTYPE.TO == TYPE
        type_id = self.get_type_id(TYPE)

        c_type_id = rmodel.inputconst(lltype.Signed, type_id)
        info = self.type_info_list[type_id]
        c_size = rmodel.inputconst(lltype.Signed, info["fixedsize"])
        c_has_finalizer = rmodel.inputconst(
            lltype.Bool, bool(self.finalizer_funcptr_for_type(TYPE)))

        if not op.opname.endswith('_varsize'):
            #malloc_ptr = self.malloc_fixedsize_ptr
            zero = flags.get('zero', False)
            if zero:
                malloc_ptr = self.malloc_fixedsize_clear_ptr
            else:
                malloc_ptr = self.malloc_fixedsize_ptr
            args = [self.c_const_gc, c_type_id, c_size, c_can_collect,
                    c_has_finalizer, rmodel.inputconst(lltype.Bool, False)]
        else:
            v_length = op.args[-1]
            c_ofstolength = rmodel.inputconst(lltype.Signed, info['ofstolength'])
            c_varitemsize = rmodel.inputconst(lltype.Signed, info['varitemsize'])
            malloc_ptr = self.malloc_varsize_clear_ptr
##             if op.opname.startswith('zero'):
##                 malloc_ptr = self.malloc_varsize_clear_ptr
##             else:
##                 malloc_ptr = self.malloc_varsize_clear_ptr
            args = [self.c_const_gc, c_type_id, v_length, c_size,
                    c_varitemsize, c_ofstolength, c_can_collect,
                    c_has_finalizer]
        self.push_roots(hop)
        v_result = hop.genop("direct_call", [malloc_ptr] + args,
                             resulttype=llmemory.GCREF)
        self.pop_roots(hop)
        return v_result

    gct_fv_gc_malloc_varsize = gct_fv_gc_malloc

    def gct_gc__collect(self, hop):
        op = hop.spaceop
        self.push_roots(hop)
        hop.genop("direct_call", [self.collect_ptr, self.c_const_gc],
                  resultvar=op.result)
        self.pop_roots(hop)

    def gct_gc_x_swap_pool(self, hop):
        op = hop.spaceop
        [v_malloced] = op.args
        hop.genop("direct_call",
                  [self.x_swap_pool_ptr, self.c_const_gc, v_malloced],
                  resultvar=op.result)

    def gct_gc_x_clone(self, hop):
        op = hop.spaceop
        [v_clonedata] = op.args
        hop.genop("direct_call",
                  [self.x_clone_ptr, self.c_const_gc, v_clonedata],
                  resultvar=op.result)

    def gct_gc_x_size_header(self, hop):
        op = hop.spaceop
        c_result = rmodel.inputconst(lltype.Signed,
                                     self.gcdata.gc.size_gc_header())
        hop.genop("same_as",
                  [c_result],
                  resultvar=op.result)

    def gct_gc_x_become(self, hop):
        op = hop.spaceop
        [v_target, v_source] = op.args
        self.push_roots(hop)
        hop.genop("direct_call",
                  [self.x_become_ptr, self.c_const_gc, v_target, v_source],
                  resultvar=op.result)
        self.pop_roots(hop)

    def gct_zero_gc_pointers_inside(self, hop):
        v_ob = hop.spaceop.args[0]
        TYPE = v_ob.concretetype.TO
        gen_zero_gc_pointers(TYPE, v_ob, hop.llops)

    def gct_weakref_create(self, hop):
        op = hop.spaceop

        type_id = self.get_type_id(WEAKREF)

        c_type_id = rmodel.inputconst(lltype.Signed, type_id)
        info = self.type_info_list[type_id]
        c_size = rmodel.inputconst(lltype.Signed, info["fixedsize"])
        malloc_ptr = self.malloc_fixedsize_ptr
        c_has_finalizer = rmodel.inputconst(lltype.Bool, False)
        c_has_weakptr = c_can_collect = rmodel.inputconst(lltype.Bool, True)
        args = [self.c_const_gc, c_type_id, c_size, c_can_collect,
                c_has_finalizer, c_has_weakptr]

        v_instance, = op.args
        v_addr = hop.genop("cast_ptr_to_adr", [v_instance],
                           resulttype=llmemory.Address)
        self.push_roots(hop)
        v_result = hop.genop("direct_call", [malloc_ptr] + args,
                             resulttype=llmemory.GCREF)
        v_result = hop.genop("cast_opaque_ptr", [v_result],
                            resulttype=WEAKREFPTR)
        self.pop_roots(hop)
        hop.genop("bare_setfield",
                  [v_result, rmodel.inputconst(lltype.Void, "weakptr"), v_addr])
        v_weakref = hop.genop("cast_ptr_to_weakrefptr", [v_result],
                              resulttype=llmemory.WeakRefPtr)
        hop.cast_result(v_weakref)

    def gct_weakref_deref(self, hop):
        v_wref, = hop.spaceop.args
        v_addr = hop.genop("direct_call",
                           [self.weakref_deref_ptr, v_wref],
                           resulttype=llmemory.Address)
        hop.cast_result(v_addr)

    def push_alive_nopyobj(self, var, llops):
        pass

    def pop_alive_nopyobj(self, var, llops):
        pass

    def push_roots(self, hop):
        if self.push_root_ptr is None:
            return
        livevars = [var for var in self.livevars if not var_ispyobj(var)]
        c_len = rmodel.inputconst(lltype.Signed, len(livevars) )
        base_addr = hop.genop("direct_call", [self.incr_stack_ptr, c_len ],
                              resulttype=llmemory.Address)
        for k,var in enumerate(livevars):
            c_k = rmodel.inputconst(lltype.Signed, k)
            v_adr = gen_cast(hop.llops, llmemory.Address, var)
            hop.genop("direct_call", [self.save_addr_ptr, base_addr, c_k, v_adr])

    def pop_roots(self, hop):
        if self.pop_root_ptr is None:
            return
        livevars = [var for var in self.livevars if not var_ispyobj(var)]
        c_len = rmodel.inputconst(lltype.Signed, len(livevars) )
        hop.genop("direct_call", [self.decr_stack_ptr, c_len ] )        
##         for var in livevars[::-1]:
##             # XXX specific to non-moving collectors
##             hop.genop("direct_call", [self.pop_root_ptr])
##             #hop.genop("gc_reload_possibly_moved", [var])

# XXX copied and modified from lltypelayout.py
def offsets_to_gc_pointers(TYPE):
    offsets = []
    if isinstance(TYPE, lltype.Struct):
        for name in TYPE._names:
            FIELD = getattr(TYPE, name)
            if isinstance(FIELD, lltype.Array):
                continue    # skip inlined array
            baseofs = llmemory.offsetof(TYPE, name)
            suboffsets = offsets_to_gc_pointers(FIELD)
            for s in suboffsets:
                try:
                    knownzero = s == 0
                except TypeError:
                    knownzero = False
                if knownzero:
                    offsets.append(baseofs)
                else:
                    offsets.append(baseofs + s)
        # sanity check
        #ex = lltype.Ptr(TYPE)._example()
        #adr = llmemory.cast_ptr_to_adr(ex)
        #for off in offsets:
        #    (adr + off)
    elif isinstance(TYPE, lltype.Ptr) and TYPE.TO._gckind == 'gc':
        offsets.append(0)
    return offsets

def weakpointer_offset(TYPE):
    if TYPE == WEAKREF:
        return llmemory.offsetof(WEAKREF, "weakptr")
    return -1

def gen_zero_gc_pointers(TYPE, v, llops):
    assert isinstance(TYPE, lltype.Struct)
    for name in TYPE._names:
        FIELD = getattr(TYPE, name)
        if isinstance(FIELD, lltype.Ptr) and FIELD._needsgc():
            c_name = rmodel.inputconst(lltype.Void, name)
            c_null = rmodel.inputconst(FIELD, lltype.nullptr(FIELD.TO))
            llops.genop('bare_setfield', [v, c_name, c_null])
        elif isinstance(FIELD, lltype.Struct):
            c_name = rmodel.inputconst(lltype.Void, name)
            v1 = llops.genop('getsubstruct', [v, c_name],
                             resulttype = lltype.Ptr(FIELD))
            gen_zero_gc_pointers(FIELD, v1, llops)

def gc_pointers_inside(v, adr):
    t = lltype.typeOf(v)
    if isinstance(t, lltype.Struct):
        for n, t2 in t._flds.iteritems():
            if isinstance(t2, lltype.Ptr) and t2.TO._gckind == 'gc':
                yield adr + llmemory.offsetof(t, n)
            elif isinstance(t2, (lltype.Array, lltype.Struct)):
                for a in gc_pointers_inside(getattr(v, n), adr + llmemory.offsetof(t, n)):
                    yield a
    elif isinstance(t, lltype.Array):
        if isinstance(t.OF, lltype.Ptr) and t2._needsgc():
            for i in range(len(v.items)):
                yield adr + llmemory.itemoffsetof(t, i)
        elif isinstance(t.OF, lltype.Struct):
            for i in range(len(v.items)):
                for a in gc_pointers_inside(v.items[i], adr + llmemory.itemoffsetof(t, i)):
                    yield a


########## weakrefs ##########
# framework: weakref objects are small structures containing only an address

WEAKREF = lltype.GcStruct("weakref", ("weakptr", llmemory.Address))
WEAKREFPTR = lltype.Ptr(WEAKREF)
sizeof_weakref= llmemory.sizeof(WEAKREF)
empty_weakref = lltype.malloc(WEAKREF, immortal=True)
empty_weakref.weakptr = llmemory.NULL

def ll_weakref_deref(wref):
    wref = llmemory.cast_weakrefptr_to_ptr(WEAKREFPTR, wref)
    if wref:
        return wref.weakptr
    return llmemory.NULL

def convert_weakref_to(targetptr):
    # Prebuilt weakrefs don't really need to be weak at all,
    # but we need to emulate the structure expected by ll_weakref_deref().
    if not targetptr:
        return empty_weakref
    else:
        link = lltype.malloc(WEAKREF, immortal=True)
        link.weakptr = llmemory.cast_ptr_to_adr(targetptr)
        return link
