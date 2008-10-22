from pypy.rpython.memory.gctransform.transform import GCTransformer
from pypy.rpython.memory.gctransform.support import find_gc_ptrs_in_type, \
     get_rtti, ll_call_destructor, type_contains_pyobjs, var_ispyobj
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython import rmodel
from pypy.rpython.memory import gctypelayout
from pypy.rpython.memory.gc import marksweep
from pypy.rpython.memory.gcheader import GCHeaderBuilder
from pypy.rlib.rarithmetic import ovfcheck
from pypy.rlib import rstack
from pypy.rlib.debug import ll_assert
from pypy.translator.backendopt import graphanalyze
from pypy.translator.backendopt.support import var_needsgc
from pypy.annotation import model as annmodel
from pypy.rpython import annlowlevel
from pypy.rpython.rbuiltin import gen_cast
from pypy.rpython.memory.gctypelayout import ll_weakref_deref, WEAKREF
from pypy.rpython.memory.gctypelayout import convert_weakref_to, WEAKREFPTR
from pypy.rpython.memory.gctransform.log import log
from pypy.tool.sourcetools import func_with_new_name
from pypy.rpython.lltypesystem.lloperation import llop, LL_OPERATIONS
import sys


class CollectAnalyzer(graphanalyze.GraphAnalyzer):

    def analyze_direct_call(self, graph, seen=None):
        try:
            func = graph.func
            if func is rstack.stack_check:
                return self.translator.config.translation.stackless
            if func._gctransformer_hint_cannot_collect_:
                return False
        except AttributeError:
            pass
        return graphanalyze.GraphAnalyzer.analyze_direct_call(self, graph,
                                                              seen)
    
    def operation_is_true(self, op):
        if op.opname in ('malloc', 'malloc_varsize'):
            flags = op.args[1].value
            return flags['flavor'] == 'gc' and not flags.get('nocollect', False)
        else:
            return (op.opname in LL_OPERATIONS and
                    LL_OPERATIONS[op.opname].canunwindgc)

def find_initializing_stores(collect_analyzer, graph):
    from pypy.objspace.flow.model import mkentrymap
    entrymap = mkentrymap(graph)
    # a bit of a hackish analysis: if a block contains a malloc and check that
    # the result is not zero, then the block following the True link will
    # usually initialize the newly allocated object
    result = {}
    def find_in_block(block, mallocvars):
        for i, op in enumerate(block.operations):
            if op.opname in ("cast_pointer", "same_as"):
                if op.args[0] in mallocvars:
                    mallocvars[op.result] = True
            elif op.opname in ("setfield", "setarrayitem", "setinteriorfield"):
                TYPE = op.args[-1].concretetype
                if (op.args[0] in mallocvars and
                    isinstance(TYPE, lltype.Ptr) and
                    TYPE.TO._gckind == "gc"):
                    result[op] = True
            else:
                if collect_analyzer.analyze(op):
                    return
        for exit in block.exits:
            if len(entrymap[exit.target]) != 1:
                continue
            newmallocvars = {}
            for i, var in enumerate(exit.args):
                if var in mallocvars:
                    newmallocvars[exit.target.inputargs[i]] = True
            if newmallocvars:
                find_in_block(exit.target, newmallocvars)
    mallocnum = 0
    blockset = set(graph.iterblocks())
    while blockset:
        block = blockset.pop()
        if len(block.operations) < 2:
            continue
        mallocop = block.operations[-2]
        checkop = block.operations[-1]
        if not (mallocop.opname == "malloc" and
                checkop.opname == "ptr_nonzero" and
                mallocop.result is checkop.args[0] and
                block.exitswitch is checkop.result):
            continue
        exits = [exit for exit in block.exits if exit.llexitcase]
        if len(exits) != 1:
            continue
        exit = exits[0]
        if len(entrymap[exit.target]) != 1:
            continue
        try:
            index = exit.args.index(mallocop.result)
        except ValueError:
            continue
        target = exit.target
        mallocvars = {target.inputargs[index]: True}
        mallocnum += 1
        find_in_block(target, mallocvars)
    #if result:
    #    print "found %s initializing stores in %s" % (len(result), graph.name)
    return result

class FrameworkGCTransformer(GCTransformer):
    use_stackless = False
    root_stack_depth = 163840

    def __init__(self, translator):
        from pypy.rpython.memory.gc.base import choose_gc_from_config
        super(FrameworkGCTransformer, self).__init__(translator, inline=True)
        if hasattr(self, 'GC_PARAMS'):
            # for tests: the GC choice can be specified as class attributes
            from pypy.rpython.memory.gc.marksweep import MarkSweepGC
            GCClass = getattr(self, 'GCClass', MarkSweepGC)
            GC_PARAMS = self.GC_PARAMS
        else:
            # for regular translation: pick the GC from the config
            GCClass, GC_PARAMS = choose_gc_from_config(translator.config)

        self.layoutbuilder = TransformerLayoutBuilder(self)
        self.get_type_id = self.layoutbuilder.get_type_id

        # set up dummy a table, to be overwritten with the real one in finish()
        type_info_table = lltype._ptr(
            lltype.Ptr(gctypelayout.GCData.TYPE_INFO_TABLE),
            "delayed!type_info_table", solid=True)
        gcdata = gctypelayout.GCData(type_info_table)

        # initialize the following two fields with a random non-NULL address,
        # to make the annotator happy.  The fields are patched in finish()
        # to point to a real array.
        foo = lltype.malloc(lltype.FixedSizeArray(llmemory.Address, 1),
                            immortal=True, zero=True)
        a_random_address = llmemory.cast_ptr_to_adr(foo)
        gcdata.static_root_start = a_random_address      # patched in finish()
        gcdata.static_root_nongcend = a_random_address   # patched in finish()
        gcdata.static_root_end = a_random_address        # patched in finish()
        self.gcdata = gcdata
        self.malloc_fnptr_cache = {}

        gcdata.gc = GCClass(translator.config.translation, **GC_PARAMS)
        root_walker = self.build_root_walker()
        gcdata.set_query_functions(gcdata.gc)
        gcdata.gc.set_root_walker(root_walker)
        self.num_pushs = 0
        self.write_barrier_calls = 0

        def frameworkgc_setup():
            # run-time initialization code
            root_walker.setup_root_walker()
            gcdata.gc.setup()

        bk = self.translator.annotator.bookkeeper

        # the point of this little dance is to not annotate
        # self.gcdata.static_root_xyz as constants. XXX is it still needed??
        data_classdef = bk.getuniqueclassdef(gctypelayout.GCData)
        data_classdef.generalize_attr(
            'static_root_start',
            annmodel.SomeAddress())
        data_classdef.generalize_attr(
            'static_root_nongcend',
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
        if root_walker.need_root_stack:
            self.incr_stack_ptr = getfn(root_walker.incr_stack,
                                       [annmodel.SomeInteger()],
                                       annmodel.SomeAddress(),
                                       inline = True)
            self.decr_stack_ptr = getfn(root_walker.decr_stack,
                                       [annmodel.SomeInteger()],
                                       annmodel.SomeAddress(),
                                       inline = True)
        else:
            self.incr_stack_ptr = None
            self.decr_stack_ptr = None
        self.weakref_deref_ptr = self.inittime_helper(
            ll_weakref_deref, [llmemory.WeakRefPtr], llmemory.Address)
        
        classdef = bk.getuniqueclassdef(GCClass)
        s_gc = annmodel.SomeInstance(classdef)
        s_gcref = annmodel.SomePtr(llmemory.GCREF)

        malloc_fixedsize_clear_meth = GCClass.malloc_fixedsize_clear.im_func
        self.malloc_fixedsize_clear_ptr = getfn(
            malloc_fixedsize_clear_meth,
            [s_gc, annmodel.SomeInteger(nonneg=True),
             annmodel.SomeInteger(nonneg=True),
             annmodel.SomeBool(), annmodel.SomeBool(),
             annmodel.SomeBool()], s_gcref,
            inline = False)
        if hasattr(GCClass, 'malloc_fixedsize'):
            malloc_fixedsize_meth = GCClass.malloc_fixedsize.im_func
            self.malloc_fixedsize_ptr = getfn(
                malloc_fixedsize_meth,
                [s_gc, annmodel.SomeInteger(nonneg=True),
                 annmodel.SomeInteger(nonneg=True),
                 annmodel.SomeBool(), annmodel.SomeBool(),
                 annmodel.SomeBool()], s_gcref,
                inline = False)
        else:
            malloc_fixedsize_meth = None
            self.malloc_fixedsize_ptr = self.malloc_fixedsize_clear_ptr
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
        self.can_move_ptr = getfn(GCClass.can_move.im_func,
                                  [s_gc, annmodel.SomeAddress()],
                                  annmodel.SomeBool())

        # in some GCs we can inline the common case of
        # malloc_fixedsize(typeid, size, True, False, False)
        if getattr(GCClass, 'inline_simple_malloc', False):
            # make a copy of this function so that it gets annotated
            # independently and the constants are folded inside
            if malloc_fixedsize_meth is None:
                malloc_fast_meth = malloc_fixedsize_clear_meth
                self.malloc_fast_is_clearing = True
            else:
                malloc_fast_meth = malloc_fixedsize_meth
                self.malloc_fast_is_clearing = False
            malloc_fast = func_with_new_name(
                malloc_fast_meth,
                "malloc_fast")
            s_False = annmodel.SomeBool(); s_False.const = False
            s_True  = annmodel.SomeBool(); s_True .const = True
            self.malloc_fast_ptr = getfn(
                malloc_fast,
                [s_gc, annmodel.SomeInteger(nonneg=True),
                 annmodel.SomeInteger(nonneg=True),
                 s_True, s_False,
                 s_False], s_gcref,
                inline = True)
        else:
            self.malloc_fast_ptr = None

        # in some GCs we can also inline the common case of
        # malloc_varsize(typeid, length, (3 constant sizes), True, False)
        if getattr(GCClass, 'inline_simple_malloc_varsize', False):
            # make a copy of this function so that it gets annotated
            # independently and the constants are folded inside
            malloc_varsize_clear_fast = func_with_new_name(
                GCClass.malloc_varsize_clear.im_func,
                "malloc_varsize_clear_fast")
            s_False = annmodel.SomeBool(); s_False.const = False
            s_True  = annmodel.SomeBool(); s_True .const = True
            self.malloc_varsize_clear_fast_ptr = getfn(
                malloc_varsize_clear_fast,
                [s_gc, annmodel.SomeInteger(nonneg=True),
                 annmodel.SomeInteger(nonneg=True),
                 annmodel.SomeInteger(nonneg=True),
                 annmodel.SomeInteger(nonneg=True),
                 annmodel.SomeInteger(nonneg=True),
                 s_True, s_False], s_gcref,
                inline = True)
        else:
            self.malloc_varsize_clear_fast_ptr = None

        if getattr(GCClass, 'malloc_varsize_nonmovable', False):
            malloc_nonmovable = func_with_new_name(
                GCClass.malloc_varsize_nonmovable.im_func,
                "malloc_varsize_nonmovable")
            self.malloc_varsize_nonmovable_ptr = getfn(
                malloc_nonmovable,
                [s_gc, annmodel.SomeInteger(nonneg=True),
                 annmodel.SomeInteger(nonneg=True)], s_gcref)
        else:
            self.malloc_varsize_nonmovable_ptr = None

        if getattr(GCClass, 'malloc_varsize_resizable', False):
            malloc_resizable = func_with_new_name(
                GCClass.malloc_varsize_resizable.im_func,
                "malloc_varsize_resizable")
            self.malloc_varsize_resizable_ptr = getfn(
                malloc_resizable,
                [s_gc, annmodel.SomeInteger(nonneg=True),
                 annmodel.SomeInteger(nonneg=True)], s_gcref)
        else:
            self.malloc_varsize_resizable_ptr = None

        if getattr(GCClass, 'realloc', False):
            self.realloc_ptr = getfn(
                GCClass.realloc.im_func,
                [s_gc, s_gcref] +
                [annmodel.SomeInteger(nonneg=True)] * 4 +
                [annmodel.SomeBool()],
                s_gcref)

        if GCClass.moving_gc:
            self.id_ptr = getfn(GCClass.id.im_func,
                                [s_gc, s_gcref], annmodel.SomeInteger(),
                                inline = False,
                                minimal_transform = False)
        else:
            self.id_ptr = None

        self.set_max_heap_size_ptr = getfn(GCClass.set_max_heap_size.im_func,
                                           [s_gc,
                                            annmodel.SomeInteger(nonneg=True)],
                                           annmodel.s_None)

        if GCClass.needs_write_barrier:
            self.write_barrier_ptr = getfn(GCClass.write_barrier.im_func,
                                           [s_gc,
                                            annmodel.SomeAddress(),
                                            annmodel.SomeAddress()],
                                           annmodel.s_None,
                                           inline=True)
        else:
            self.write_barrier_ptr = None
        self.statistics_ptr = getfn(GCClass.statistics.im_func,
                                    [s_gc, annmodel.SomeInteger()],
                                    annmodel.SomeInteger())

        # experimental gc_x_* operations
        s_x_pool  = annmodel.SomePtr(marksweep.X_POOL_PTR)
        s_x_clone = annmodel.SomePtr(marksweep.X_CLONE_PTR)
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

        # thread support
        if translator.config.translation.thread:
            if not hasattr(root_walker, "need_thread_support"):
                raise Exception("%s does not support threads" % (
                    root_walker.__class__.__name__,))
            root_walker.need_thread_support()
            self.thread_prepare_ptr = getfn(root_walker.thread_prepare,
                                            [], annmodel.s_None)
            self.thread_run_ptr = getfn(root_walker.thread_run,
                                        [], annmodel.s_None,
                                        inline=True)
            self.thread_die_ptr = getfn(root_walker.thread_die,
                                        [], annmodel.s_None)

        annhelper.finish()   # at this point, annotate all mix-level helpers
        annhelper.backend_optimize()

        self.collect_analyzer = CollectAnalyzer(self.translator)
        self.collect_analyzer.analyze_all()

        s_gc = self.translator.annotator.bookkeeper.valueoftype(GCClass)
        r_gc = self.translator.rtyper.getrepr(s_gc)
        self.c_const_gc = rmodel.inputconst(r_gc, self.gcdata.gc)
        self.malloc_zero_filled = GCClass.malloc_zero_filled

        HDR = self._gc_HDR = self.gcdata.gc.gcheaderbuilder.HDR
        self._gc_fields = fields = []
        for fldname in HDR._names:
            FLDTYPE = getattr(HDR, fldname)
            fields.append(('_' + fldname, FLDTYPE))

    def build_root_walker(self):
        return ShadowStackRootWalker(self)

    def consider_constant(self, TYPE, value):
        self.layoutbuilder.consider_constant(TYPE, value, self.gcdata.gc)

    #def get_type_id(self, TYPE):
    #    this method is attached to the instance and redirects to
    #    layoutbuilder.get_type_id().

    def finalizer_funcptr_for_type(self, TYPE):
        return self.layoutbuilder.finalizer_funcptr_for_type(TYPE)

    def gc_fields(self):
        return self._gc_fields

    def gc_field_values_for(self, obj):
        hdr = self.gcdata.gc.gcheaderbuilder.header_of_object(obj)
        HDR = self._gc_HDR
        return [getattr(hdr, fldname) for fldname in HDR._names]

    def finish_tables(self):
        table = self.layoutbuilder.flatten_table()
        log.info("assigned %s typeids" % (len(table), ))
        log.info("added %s push/pop stack root instructions" % (
                     self.num_pushs, ))
        if self.write_barrier_ptr:
            log.info("inserted %s write barrier calls" % (
                         self.write_barrier_calls, ))

        # replace the type_info_table pointer in gcdata -- at this point,
        # the database is in principle complete, so it has already seen
        # the delayed pointer.  We need to force it to consider the new
        # array now.

        self.gcdata.type_info_table._become(table)

        # XXX because we call inputconst already in replace_malloc, we can't
        # modify the instance, we have to modify the 'rtyped instance'
        # instead.  horrors.  is there a better way?

        s_gcdata = self.translator.annotator.bookkeeper.immutablevalue(
            self.gcdata)
        r_gcdata = self.translator.rtyper.getrepr(s_gcdata)
        ll_instance = rmodel.inputconst(r_gcdata, self.gcdata).value

        addresses_of_static_ptrs = (
            self.layoutbuilder.addresses_of_static_ptrs_in_nongc +
            self.layoutbuilder.addresses_of_static_ptrs)
        log.info("found %s static roots" % (len(addresses_of_static_ptrs), ))
        ll_static_roots_inside = lltype.malloc(lltype.Array(llmemory.Address),
                                               len(addresses_of_static_ptrs),
                                               immortal=True)
        for i in range(len(addresses_of_static_ptrs)):
            ll_static_roots_inside[i] = addresses_of_static_ptrs[i]
        ll_instance.inst_static_root_start = llmemory.cast_ptr_to_adr(ll_static_roots_inside) + llmemory.ArrayItemsOffset(lltype.Array(llmemory.Address))
        ll_instance.inst_static_root_nongcend = ll_instance.inst_static_root_start + llmemory.sizeof(llmemory.Address) * len(self.layoutbuilder.addresses_of_static_ptrs_in_nongc)
        ll_instance.inst_static_root_end = ll_instance.inst_static_root_start + llmemory.sizeof(llmemory.Address) * len(addresses_of_static_ptrs)

        newgcdependencies = []
        newgcdependencies.append(ll_static_roots_inside)
        self.write_typeid_list()
        return newgcdependencies

    def write_typeid_list(self):
        """write out the list of type ids together with some info"""
        from pypy.tool.udir import udir
        # XXX not ideal since it is not per compilation, but per run
        f = udir.join("typeids.txt").open("w")
        all = [(typeid, TYPE)
               for TYPE, typeid in self.layoutbuilder.id_of_type.iteritems()]
        all.sort()
        for typeid, TYPE in all:
            f.write("%s %s\n" % (typeid, TYPE))
        f.close()

    def transform_graph(self, graph):
        if self.write_barrier_ptr:
            self.initializing_stores = find_initializing_stores(
                self.collect_analyzer, graph)
        super(FrameworkGCTransformer, self).transform_graph(graph)
        if self.write_barrier_ptr:
            self.initializing_stores = None

    def gct_direct_call(self, hop):
        if self.collect_analyzer.analyze(hop.spaceop):
            livevars = self.push_roots(hop)
            self.default(hop)
            self.pop_roots(hop, livevars)
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
        info = self.layoutbuilder.type_info_list[type_id]
        c_size = rmodel.inputconst(lltype.Signed, info.fixedsize)
        has_finalizer = bool(self.finalizer_funcptr_for_type(TYPE))
        c_has_finalizer = rmodel.inputconst(lltype.Bool, has_finalizer)

        if not op.opname.endswith('_varsize') and not flags.get('varsize'):
            #malloc_ptr = self.malloc_fixedsize_ptr
            zero = flags.get('zero', False)
            if (self.malloc_fast_ptr is not None and
                c_can_collect.value and not c_has_finalizer.value and
                (self.malloc_fast_is_clearing or not zero)):
                malloc_ptr = self.malloc_fast_ptr
            elif zero:
                malloc_ptr = self.malloc_fixedsize_clear_ptr
            else:
                malloc_ptr = self.malloc_fixedsize_ptr
            args = [self.c_const_gc, c_type_id, c_size, c_can_collect,
                    c_has_finalizer, rmodel.inputconst(lltype.Bool, False)]
        else:
            v_length = op.args[-1]
            c_ofstolength = rmodel.inputconst(lltype.Signed, info.ofstolength)
            c_varitemsize = rmodel.inputconst(lltype.Signed, info.varitemsize)
            if flags.get('resizable') and self.malloc_varsize_resizable_ptr:
                assert c_can_collect.value
                assert not c_has_finalizer.value
                malloc_ptr = self.malloc_varsize_resizable_ptr
                args = [self.c_const_gc, c_type_id, v_length]                
            elif flags.get('nonmovable') and self.malloc_varsize_nonmovable_ptr:
                # we don't have tests for such cases, let's fail
                # explicitely
                assert c_can_collect.value
                assert not c_has_finalizer.value
                malloc_ptr = self.malloc_varsize_nonmovable_ptr
                args = [self.c_const_gc, c_type_id, v_length]
            else:
                if (self.malloc_varsize_clear_fast_ptr is not None and
                    c_can_collect.value and not c_has_finalizer.value):
                    malloc_ptr = self.malloc_varsize_clear_fast_ptr
                else:
                    malloc_ptr = self.malloc_varsize_clear_ptr
                args = [self.c_const_gc, c_type_id, v_length, c_size,
                        c_varitemsize, c_ofstolength, c_can_collect,
                        c_has_finalizer]
        keep_current_args = flags.get('keep_current_args', False)
        livevars = self.push_roots(hop, keep_current_args=keep_current_args)
        v_result = hop.genop("direct_call", [malloc_ptr] + args,
                             resulttype=llmemory.GCREF)
        self.pop_roots(hop, livevars)
        return v_result

    gct_fv_gc_malloc_varsize = gct_fv_gc_malloc

    def gct_gc__collect(self, hop):
        op = hop.spaceop
        livevars = self.push_roots(hop)
        hop.genop("direct_call", [self.collect_ptr, self.c_const_gc],
                  resultvar=op.result)
        self.pop_roots(hop, livevars)

    def gct_gc_can_move(self, hop):
        op = hop.spaceop
        v_addr = hop.genop('cast_ptr_to_adr',
                           [op.args[0]], resulttype=llmemory.Address)
        hop.genop("direct_call", [self.can_move_ptr, self.c_const_gc, v_addr],
                  resultvar=op.result)

    def _can_realloc(self):
        return self.gcdata.gc.can_realloc

    def perform_realloc(self, hop, v_ptr, v_newsize, c_const_size,
                        c_itemsize, c_lengthofs, c_grow):
        vlist = [self.realloc_ptr, self.c_const_gc, v_ptr, v_newsize,
                 c_const_size, c_itemsize, c_lengthofs, c_grow]
        livevars = self.push_roots(hop)
        v_result = hop.genop('direct_call', vlist,
                             resulttype=llmemory.GCREF)
        self.pop_roots(hop, livevars)
        return v_result

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

    def gct_zero_gc_pointers_inside(self, hop):
        if not self.malloc_zero_filled:
            v_ob = hop.spaceop.args[0]
            TYPE = v_ob.concretetype.TO
            gen_zero_gc_pointers(TYPE, v_ob, hop.llops)

    def gct_weakref_create(self, hop):
        op = hop.spaceop

        type_id = self.get_type_id(WEAKREF)

        c_type_id = rmodel.inputconst(lltype.Signed, type_id)
        info = self.layoutbuilder.type_info_list[type_id]
        c_size = rmodel.inputconst(lltype.Signed, info.fixedsize)
        malloc_ptr = self.malloc_fixedsize_ptr
        c_has_finalizer = rmodel.inputconst(lltype.Bool, False)
        c_has_weakptr = c_can_collect = rmodel.inputconst(lltype.Bool, True)
        args = [self.c_const_gc, c_type_id, c_size, c_can_collect,
                c_has_finalizer, c_has_weakptr]

        # push and pop the current live variables *including* the argument
        # to the weakref_create operation, which must be kept alive and
        # moved if the GC needs to collect
        livevars = self.push_roots(hop, keep_current_args=True)
        v_result = hop.genop("direct_call", [malloc_ptr] + args,
                             resulttype=llmemory.GCREF)
        v_result = hop.genop("cast_opaque_ptr", [v_result],
                            resulttype=WEAKREFPTR)
        self.pop_roots(hop, livevars)
        # cast_ptr_to_adr must be done after malloc, as the GC pointer
        # might have moved just now.
        v_instance, = op.args
        v_addr = hop.genop("cast_ptr_to_adr", [v_instance],
                           resulttype=llmemory.Address)
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

    def gct_gc_id(self, hop):
        if self.id_ptr is not None:
            livevars = self.push_roots(hop)
            [v_ptr] = hop.spaceop.args
            v_ptr = hop.genop("cast_opaque_ptr", [v_ptr],
                              resulttype=llmemory.GCREF)
            hop.genop("direct_call", [self.id_ptr, self.c_const_gc, v_ptr],
                      resultvar=hop.spaceop.result)
            self.pop_roots(hop, livevars)
        else:
            hop.rename('cast_ptr_to_int')     # works nicely for non-moving GCs

    def gct_gc_set_max_heap_size(self, hop):
        [v_size] = hop.spaceop.args
        hop.genop("direct_call", [self.set_max_heap_size_ptr,
                                  self.c_const_gc,
                                  v_size])

    def gct_gc_thread_prepare(self, hop):
        assert self.translator.config.translation.thread
        hop.genop("direct_call", [self.thread_prepare_ptr])

    def gct_gc_thread_run(self, hop):
        assert self.translator.config.translation.thread
        hop.genop("direct_call", [self.thread_run_ptr])

    def gct_gc_thread_die(self, hop):
        assert self.translator.config.translation.thread
        hop.genop("direct_call", [self.thread_die_ptr])

    def gct_malloc_nonmovable_varsize(self, hop):
        TYPE = hop.spaceop.result.concretetype
        if self.gcdata.gc.can_malloc_nonmovable():
            return self.gct_malloc_varsize(hop, {'nonmovable':True})
        c = rmodel.inputconst(TYPE, lltype.nullptr(TYPE.TO))
        return hop.cast_result(c)

    def gct_malloc_nonmovable(self, hop):
        TYPE = hop.spaceop.result.concretetype
        if self.gcdata.gc.can_malloc_nonmovable():
            return self.gct_malloc(hop, {'nonmovable':True})
        c = rmodel.inputconst(TYPE, lltype.nullptr(TYPE.TO))
        return hop.cast_result(c)

    def transform_generic_set(self, hop):
        from pypy.objspace.flow.model import Constant
        opname = hop.spaceop.opname
        v_struct = hop.spaceop.args[0]
        v_newvalue = hop.spaceop.args[-1]
        assert opname in ('setfield', 'setarrayitem', 'setinteriorfield')
        assert isinstance(v_newvalue.concretetype, lltype.Ptr)
        # XXX for some GCs the skipping if the newvalue is a constant won't be
        # ok
        if (self.write_barrier_ptr is not None
            and not isinstance(v_newvalue, Constant)
            and v_struct.concretetype.TO._gckind == "gc"
            and hop.spaceop not in self.initializing_stores):
            self.write_barrier_calls += 1
            v_newvalue = hop.genop("cast_ptr_to_adr", [v_newvalue],
                                   resulttype = llmemory.Address)
            v_structaddr = hop.genop("cast_ptr_to_adr", [v_struct],
                                     resulttype = llmemory.Address)
            hop.genop("direct_call", [self.write_barrier_ptr,
                                      self.c_const_gc,
                                      v_newvalue,
                                      v_structaddr])
        hop.rename('bare_' + opname)

    def var_needs_set_transform(self, var):
        return var_needsgc(var)

    def push_alive_nopyobj(self, var, llops):
        pass

    def pop_alive_nopyobj(self, var, llops):
        pass

    def get_livevars_for_roots(self, hop, keep_current_args=False):
        if self.gcdata.gc.moving_gc and not keep_current_args:
            # moving GCs don't borrow, so the caller does not need to keep
            # the arguments alive
            livevars = [var for var in hop.livevars_after_op()
                            if not var_ispyobj(var)]
        else:
            livevars = hop.livevars_after_op() + hop.current_op_keeps_alive()
            livevars = [var for var in livevars if not var_ispyobj(var)]
        return livevars

    def push_roots(self, hop, keep_current_args=False):
        if self.incr_stack_ptr is None:
            return
        livevars = self.get_livevars_for_roots(hop, keep_current_args)
        self.num_pushs += len(livevars)
        if not livevars:
            return []
        c_len = rmodel.inputconst(lltype.Signed, len(livevars) )
        base_addr = hop.genop("direct_call", [self.incr_stack_ptr, c_len ],
                              resulttype=llmemory.Address)
        c_type = rmodel.inputconst(lltype.Void, llmemory.Address)
        for k,var in enumerate(livevars):
            c_k = rmodel.inputconst(lltype.Signed, k)
            v_adr = gen_cast(hop.llops, llmemory.Address, var)
            hop.genop("raw_store", [base_addr, c_type, c_k, v_adr])
        return livevars

    def pop_roots(self, hop, livevars):
        if self.decr_stack_ptr is None:
            return
        if not livevars:
            return
        c_len = rmodel.inputconst(lltype.Signed, len(livevars) )
        base_addr = hop.genop("direct_call", [self.decr_stack_ptr, c_len ],
                              resulttype=llmemory.Address)
        if self.gcdata.gc.moving_gc:
            # for moving collectors, reload the roots into the local variables
            c_type = rmodel.inputconst(lltype.Void, llmemory.Address)
            for k,var in enumerate(livevars):
                c_k = rmodel.inputconst(lltype.Signed, k)
                v_newaddr = hop.genop("raw_load", [base_addr, c_type, c_k],
                                      resulttype=llmemory.Address)
                hop.genop("gc_reload_possibly_moved", [v_newaddr, var])

    def compute_borrowed_vars(self, graph):
        # XXX temporary workaround, should be done more correctly
        if self.gcdata.gc.moving_gc:
            return lambda v: False
        return super(FrameworkGCTransformer, self).compute_borrowed_vars(graph)


class TransformerLayoutBuilder(gctypelayout.TypeLayoutBuilder):

    def __init__(self, transformer):
        super(TransformerLayoutBuilder, self).__init__()
        self.transformer = transformer
        self.offsettable_cache = {}

    def make_finalizer_funcptr_for_type(self, TYPE):
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
            fptr = self.transformer.annotate_finalizer(ll_finalizer,
                                                       [llmemory.Address],
                                                       lltype.Void)
        else:
            fptr = lltype.nullptr(gctypelayout.GCData.FINALIZERTYPE.TO)
        return fptr


def gen_zero_gc_pointers(TYPE, v, llops, previous_steps=None):
    if previous_steps is None:
        previous_steps = []
    assert isinstance(TYPE, lltype.Struct)
    for name in TYPE._names:
        c_name = rmodel.inputconst(lltype.Void, name)
        FIELD = getattr(TYPE, name)
        if isinstance(FIELD, lltype.Ptr) and FIELD._needsgc():
            c_null = rmodel.inputconst(FIELD, lltype.nullptr(FIELD.TO))
            if not previous_steps:
                llops.genop('bare_setfield', [v, c_name, c_null])
            else:
                llops.genop('bare_setinteriorfield',
                            [v] + previous_steps + [c_name, c_null])
        elif isinstance(FIELD, lltype.Struct):
            gen_zero_gc_pointers(FIELD, v, llops, previous_steps + [c_name])

# ____________________________________________________________


sizeofaddr = llmemory.sizeof(llmemory.Address)


class BaseRootWalker:
    need_root_stack = False

    def __init__(self, gctransformer):
        self.gcdata = gctransformer.gcdata
        self.gc = self.gcdata.gc

    def _freeze_(self):
        return True

    def setup_root_walker(self):
        pass

    def walk_roots(self, collect_stack_root,
                   collect_static_in_prebuilt_nongc,
                   collect_static_in_prebuilt_gc):
        gcdata = self.gcdata
        gc = self.gc
        if collect_static_in_prebuilt_nongc:
            addr = gcdata.static_root_start
            end = gcdata.static_root_nongcend
            while addr != end:
                result = addr.address[0]
                if result.address[0] != llmemory.NULL:
                    collect_static_in_prebuilt_nongc(gc, result)
                addr += sizeofaddr
        if collect_static_in_prebuilt_gc:
            addr = gcdata.static_root_nongcend
            end = gcdata.static_root_end
            while addr != end:
                result = addr.address[0]
                if result.address[0] != llmemory.NULL:
                    collect_static_in_prebuilt_gc(gc, result)
                addr += sizeofaddr
        if collect_stack_root:
            self.walk_stack_roots(collect_stack_root)     # abstract


class ShadowStackRootWalker(BaseRootWalker):
    need_root_stack = True
    thread_setup = None
    collect_stacks_from_other_threads = None

    def __init__(self, gctransformer):
        BaseRootWalker.__init__(self, gctransformer)
        self.rootstacksize = sizeofaddr * gctransformer.root_stack_depth
        # NB. 'self' is frozen, but we can use self.gcdata to store state
        gcdata = self.gcdata

        def incr_stack(n):
            top = gcdata.root_stack_top
            gcdata.root_stack_top = top + n*sizeofaddr
            return top
        self.incr_stack = incr_stack

        def decr_stack(n):
            top = gcdata.root_stack_top - n*sizeofaddr
            gcdata.root_stack_top = top
            return top
        self.decr_stack = decr_stack

    def push_stack(self, addr):
        top = self.incr_stack(1)
        top.address[0] = addr

    def pop_stack(self):
        top = self.decr_stack(1)
        return top.address[0]

    def allocate_stack(self):
        result = llmemory.raw_malloc(self.rootstacksize)
        if result:
            llmemory.raw_memclear(result, self.rootstacksize)
        return result

    def setup_root_walker(self):
        stackbase = self.allocate_stack()
        ll_assert(bool(stackbase), "could not allocate root stack")
        self.gcdata.root_stack_top  = stackbase
        self.gcdata.root_stack_base = stackbase
        if self.thread_setup is not None:
            self.thread_setup()

    def walk_stack_roots(self, collect_stack_root):
        gcdata = self.gcdata
        gc = self.gc
        addr = gcdata.root_stack_base
        end = gcdata.root_stack_top
        while addr != end:
            if addr.address[0] != llmemory.NULL:
                collect_stack_root(gc, addr)
            addr += sizeofaddr
        if self.collect_stacks_from_other_threads is not None:
            self.collect_stacks_from_other_threads(collect_stack_root)

    def need_thread_support(self):
        from pypy.module.thread import ll_thread    # xxx fish
        from pypy.rpython.memory.support import AddressDict
        from pypy.rpython.memory.support import copy_without_null_values
        gcdata = self.gcdata
        # the interfacing between the threads and the GC is done via
        # three completely ad-hoc operations at the moment:
        # gc_thread_prepare, gc_thread_run, gc_thread_die.
        # See docstrings below.

        def get_aid():
            """Return the thread identifier, cast to an (opaque) address."""
            return llmemory.cast_int_to_adr(ll_thread.get_ident())

        def thread_setup():
            """Called once when the program starts."""
            aid = get_aid()
            gcdata.main_thread = aid
            gcdata.active_thread = aid
            gcdata.thread_stacks = AddressDict()     # {aid: root_stack_top}
            gcdata._fresh_rootstack = llmemory.NULL
            gcdata.dead_threads_count = 0

        def thread_prepare():
            """Called just before thread.start_new_thread().  This
            allocates a new shadow stack to be used by the future
            thread.  If memory runs out, this raises a MemoryError
            (which can be handled by the caller instead of just getting
            ignored if it was raised in the newly starting thread).
            """
            if not gcdata._fresh_rootstack:
                gcdata._fresh_rootstack = self.allocate_stack()
                if not gcdata._fresh_rootstack:
                    raise MemoryError

        def thread_run():
            """Called whenever the current thread (re-)acquired the GIL.
            This should ensure that the shadow stack installed in
            gcdata.root_stack_top/root_stack_base is the one corresponding
            to the current thread.
            """
            aid = get_aid()
            if gcdata.active_thread != aid:
                switch_shadow_stacks(aid)

        def thread_die():
            """Called just before the final GIL release done by a dying
            thread.  After a thread_die(), no more gc operation should
            occur in this thread.
            """
            aid = get_aid()
            gcdata.thread_stacks.setitem(aid, llmemory.NULL)
            old = gcdata.root_stack_base
            if gcdata._fresh_rootstack == llmemory.NULL:
                gcdata._fresh_rootstack = old
            else:
                llmemory.raw_free(old)
            install_new_stack(gcdata.main_thread)
            # from time to time, rehash the dictionary to remove
            # old NULL entries
            gcdata.dead_threads_count += 1
            if (gcdata.dead_threads_count & 511) == 0:
                gcdata.thread_stacks = copy_without_null_values(
                    gcdata.thread_stacks)

        def switch_shadow_stacks(new_aid):
            save_away_current_stack()
            install_new_stack(new_aid)
        switch_shadow_stacks._dont_inline_ = True

        def save_away_current_stack():
            old_aid = gcdata.active_thread
            # save root_stack_base on the top of the stack
            self.push_stack(gcdata.root_stack_base)
            # store root_stack_top into the dictionary
            gcdata.thread_stacks.setitem(old_aid, gcdata.root_stack_top)

        def install_new_stack(new_aid):
            # look for the new stack top
            top = gcdata.thread_stacks.get(new_aid, llmemory.NULL)
            if top == llmemory.NULL:
                # first time we see this thread.  It is an error if no
                # fresh new stack is waiting.
                base = gcdata._fresh_rootstack
                gcdata._fresh_rootstack = llmemory.NULL
                ll_assert(base != llmemory.NULL, "missing gc_thread_prepare")
                gcdata.root_stack_top = base
                gcdata.root_stack_base = base
            else:
                # restore the root_stack_base from the top of the stack
                gcdata.root_stack_top = top
                gcdata.root_stack_base = self.pop_stack()
            # done
            gcdata.active_thread = new_aid

        def collect_stack(aid, stacktop, callback):
            if stacktop != llmemory.NULL and aid != get_aid():
                # collect all valid stacks from the dict (the entry
                # corresponding to the current thread is not valid)
                gc = self.gc
                end = stacktop - sizeofaddr
                addr = end.address[0]
                while addr != end:
                    if addr.address[0] != llmemory.NULL:
                        callback(gc, addr)
                    addr += sizeofaddr

        def collect_more_stacks(callback):
            gcdata.thread_stacks.foreach(collect_stack, callback)

        self.thread_setup = thread_setup
        self.thread_prepare = thread_prepare
        self.thread_run = thread_run
        self.thread_die = thread_die
        self.collect_stacks_from_other_threads = collect_more_stacks
