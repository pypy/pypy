from rpython.flowspace.model import SpaceOperation, Constant, Variable
from rpython.translator.unsimplify import varoftype, insert_empty_block
from rpython.translator.unsimplify import insert_empty_startblock
from rpython.rtyper.lltypesystem import lltype
from rpython.translator.backendopt.writeanalyze import top_set
from rpython.translator.simplify import join_blocks


MALLOCS = set([
    'malloc', 'malloc_varsize',
    'malloc_nonmovable', 'malloc_nonmovable_varsize',
    ])

def unwraplist(list_v):
    for v in list_v: 
        if isinstance(v, Constant):
            yield v.value
        elif isinstance(v, Variable):
            yield None    # unknown
        else:
            raise AssertionError(v)

def is_immutable(op):
    if op.opname in ('getfield', 'setfield'):
        STRUCT = op.args[0].concretetype.TO
        return STRUCT._immutable_field(op.args[1].value)
    if op.opname in ('getarrayitem', 'setarrayitem'):
        ARRAY = op.args[0].concretetype.TO
        return ARRAY._immutable_field()
    if op.opname == 'getinteriorfield':
        OUTER = op.args[0].concretetype.TO
        return OUTER._immutable_interiorfield(unwraplist(op.args[1:]))
    if op.opname == 'setinteriorfield':
        OUTER = op.args[0].concretetype.TO
        return OUTER._immutable_interiorfield(unwraplist(op.args[1:-1]))
    if op.opname in ('raw_load', 'raw_store'):
        return False
    raise AssertionError(op)

def needs_barrier(frm, to):
    return to > frm

def is_gc_ptr(T):
    return isinstance(T, lltype.Ptr) and T.TO._gckind == 'gc'


class Renaming(object):
    def __init__(self, newvar, category):
        self.newvar = newvar        # a Variable or a Constant
        self.TYPE = newvar.concretetype
        self.category = category


class BlockTransformer(object):

    def __init__(self, stmtransformer, block):
        self.stmtransformer = stmtransformer
        self.block = block
        self.patch = None
        self.inputargs_category = None
        self.inputargs_category_per_link = {}

    def init_start_block(self):
        from_outside = ['A'] * len(self.block.inputargs)
        self.inputargs_category_per_link[None] = from_outside
        self.update_inputargs_category()


    def analyze_inside_block(self, graph):
        gcremovetypeptr = (
            self.stmtransformer.translator.config.translation.gcremovetypeptr)
        wants_a_barrier = {}
        expand_comparison = set()
        stm_ignored = False
        for op in self.block.operations:
            is_getter = (op.opname in ('getfield', 'getarrayitem',
                                       'getinteriorfield', 'raw_load') and
                         op.result.concretetype is not lltype.Void and
                         is_gc_ptr(op.args[0].concretetype))

            if (gcremovetypeptr and op.opname in ('getfield', 'setfield') and
                op.args[1].value == 'typeptr' and
                op.args[0].concretetype.TO._hints.get('typeptr')):
                # if gcremovetypeptr, we can access directly the typeptr
                # field even on a stub
                pass

            elif (op.opname in ('getarraysize', 'getinteriorarraysize') and
                  is_gc_ptr(op.args[0].concretetype)):
                # XXX: or (is_getter and is_immutable(op))):
                # we can't leave getarraysize or the immutable getfields
                # fully unmodified: we need at least immut_read_barrier
                # to detect stubs.
                wants_a_barrier[op] = 'I'

            elif is_getter:
                # the non-immutable getfields need a regular read barrier
                wants_a_barrier[op] = 'R'

            elif (op.opname in ('setfield', 'setarrayitem',
                                'setinteriorfield', 'raw_store') and
                  op.args[-1].concretetype is not lltype.Void and
                  is_gc_ptr(op.args[0].concretetype)):
                # setfields need a regular write barrier
                T = op.args[-1].concretetype
                if is_gc_ptr(T):
                    wants_a_barrier[op] = 'W'
                else:
                    # a write of a non-gc pointer doesn't need to check for
                    # the GCFLAG_WRITEBARRIER
                    wants_a_barrier[op] = 'V'

            elif (op.opname in ('ptr_eq', 'ptr_ne') and
                  is_gc_ptr(op.args[0].concretetype)):
                # GC pointer comparison might need special care
                expand_comparison.add(op)

            elif op.opname == 'weakref_deref':
                # 'weakref_deref' needs an immutable read barrier
                wants_a_barrier[op] = 'I'

            elif op.opname == 'gc_writebarrier':
                wants_a_barrier[op] = 'W'

            elif op.opname == 'stm_ignored_start':
                assert not stm_ignored, "nested 'with stm_ignored'"
                stm_ignored = True

            elif op.opname == 'stm_ignored_stop':
                assert stm_ignored, "stm_ignored_stop without start?"
                stm_ignored = False

            if stm_ignored and op in wants_a_barrier:
                if wants_a_barrier[op] == 'W':
                    raise Exception(
                        "%r: 'with stm_ignored:' contains unsupported "
                        "operation %r writing a GC pointer" % (graph, op))
                if wants_a_barrier[op] == 'R' and is_getter and (
                        is_gc_ptr(op.result.concretetype)):
                    raise Exception(
                        "%r: 'with stm_ignored:' contains unsupported "
                        "operation %r reading a GC pointer" % (graph, op))
                assert 'I' <= wants_a_barrier[op] < 'W'
                wants_a_barrier[op] = 'I'
        #
        if stm_ignored:
            raise Exception("%r: 'with stm_ignored:' code body too complex"
                            % (graph,))
        self.wants_a_barrier = wants_a_barrier
        self.expand_comparison = expand_comparison


    def flow_through_block(self, graphinfo):

        def renfetch(v):
            try:
                return renamings[v]
            except KeyError:
                if isinstance(v, Variable):
                    ren = Renaming(v, 'A')
                else:
                    ren = Renaming(v, 'I')  # prebuilt objects cannot be stubs
                renamings[v] = ren
                return ren

        def get_category_or_null(v):
            # 'v' is an original variable here, or a constant
            if isinstance(v, Constant) and not v.value:    # a NULL constant
                return 'Z'
            if v in renamings:
                return renamings[v].category
            if isinstance(v, Constant):
                return 'I'
            else:
                return 'A'

        def renamings_get(v):
            try:
                ren = renamings[v]
            except KeyError:
                return v       # unmodified
            v2 = ren.newvar
            if v2.concretetype == v.concretetype:
                return v2
            v3 = varoftype(v.concretetype)
            newoperations.append(SpaceOperation('cast_pointer', [v2], v3))
            if lltype.castable(ren.TYPE, v3.concretetype) > 0:
                ren.TYPE = v3.concretetype
            return v3

        # note: 'renamings' maps old vars to new vars, but cast_pointers
        # are done lazily.  It means that the two vars may not have
        # exactly the same type.
        renamings = {}   # {original-var: Renaming(newvar, category)}
        newoperations = []
        stmtransformer = self.stmtransformer

        # make the initial trivial renamings needed to have some precise
        # categories for the input args
        for v, cat in zip(self.block.inputargs, self.inputargs_category):
            if is_gc_ptr(v.concretetype):
                assert cat is not None
                renamings[v] = Renaming(v, cat)

        for op in self.block.operations:
            #
            if (op.opname in ('cast_pointer', 'same_as') and
                    is_gc_ptr(op.result.concretetype)):
                renamings[op.result] = renfetch(op.args[0])
                continue
            #
            to = self.wants_a_barrier.get(op)
            if to is not None:
                ren = renfetch(op.args[0])
                frm = ren.category
                if needs_barrier(frm, to):
                    try:
                        b = stmtransformer.barrier_counts[frm, to]
                    except KeyError:
                        c_info = Constant('%s2%s' % (frm, to), lltype.Void)
                        b = [0, c_info]
                        stmtransformer.barrier_counts[frm, to] = b
                    b[0] += 1
                    c_info = b[1]
                    v = ren.newvar
                    w = varoftype(v.concretetype)
                    newop = SpaceOperation('stm_barrier', [c_info, v], w)
                    newoperations.append(newop)
                    ren.newvar = w
                    ren.category = to
            #
            newop = SpaceOperation(op.opname,
                                   [renamings_get(v) for v in op.args],
                                   op.result)
            newoperations.append(newop)
            #
            if op in self.expand_comparison:
                cats = (get_category_or_null(op.args[0]),
                        get_category_or_null(op.args[1]))
                if 'Z' not in cats and (cats[0] < 'V' or cats[1] < 'V'):
                    if newop.opname == 'ptr_ne':
                        v = varoftype(lltype.Bool)
                        negop = SpaceOperation('bool_not', [v],
                                               newop.result)
                        newoperations.append(negop)
                        newop.result = v
                    newop.opname = 'stm_ptr_eq'

            if stmtransformer.break_analyzer.analyze(op):
                # this operation can perform a transaction break:
                # all pointers are lowered to 'I', because a non-
                # stub cannot suddenly point to a stub, but we
                # cannot guarantee anything more
                for ren in renamings.values():
                    if ren.category > 'I':
                        ren.category = 'I'

            if op.opname == 'debug_stm_flush_barrier':
                for ren in renamings.values():
                    ren.category = 'A'

            if stmtransformer.collect_analyzer.analyze(op):
                # this operation can collect: we bring all 'W'
                # categories back to 'V', because we would need
                # a repeat_write_barrier on them afterwards
                for ren in renamings.values():
                    if ren.category == 'W':
                        ren.category = 'V'

            effectinfo = stmtransformer.write_analyzer.analyze(
                op, graphinfo=graphinfo)
            if effectinfo:
                if effectinfo is top_set:
                    # this operation can perform random writes: any
                    # 'R'-category object falls back to 'Q' because
                    # we would need a repeat_read_barrier()
                    for ren in renamings.values():
                        if ren.category == 'R':
                            ren.category = 'Q'
                else:
                    # the same, but only on objects of the right types
                    # -- we need to consider 'types' or any base type
                    types = set()
                    for entry in effectinfo:
                        TYPE = entry[1].TO
                        while TYPE is not None:
                            types.add(TYPE)
                            if not isinstance(TYPE, lltype.Struct):
                                break
                            _, TYPE = TYPE._first_struct()
                    for ren in renamings.values():
                        if ren.TYPE.TO in types and ren.category == 'R':
                            ren.category = 'Q'

            if op.opname in MALLOCS:
                assert op.result not in renamings
                renamings[op.result] = Renaming(op.result, 'W')

        if isinstance(self.block.exitswitch, Variable):
            switchv = renamings_get(self.block.exitswitch)
        else:
            switchv = None
        blockoperations = newoperations
        linkoperations = []
        for link in self.block.exits:
            output_categories = []
            for v in link.args:
                if is_gc_ptr(v.concretetype):
                    cat = get_category_or_null(v)
                else:
                    cat = None
                output_categories.append(cat)
            newoperations = []
            newargs = [renamings_get(v) for v in link.args]
            linkoperations.append((newargs, newoperations, output_categories))
        #
        # Record how we'd like to patch the block, but don't do any
        # patching yet
        self.patch = (blockoperations, switchv, linkoperations)


    def update_targets(self, block_transformers):
        (_, _, linkoperations) = self.patch
        assert len(linkoperations) == len(self.block.exits)
        targetbts = []
        for link, (_, _, output_categories) in zip(self.block.exits,
                                                   linkoperations):
            targetblock = link.target
            if targetblock not in block_transformers:
                continue      # ignore the exit block
            targetbt = block_transformers[targetblock]
            targetbt.inputargs_category_per_link[link] = output_categories
            if targetbt.update_inputargs_category():
                targetbts.append(targetbt)
        return set(targetbts)

    def update_inputargs_category(self):
        values = self.inputargs_category_per_link.values()
        newcats = []
        for i, v in enumerate(self.block.inputargs):
            if is_gc_ptr(v.concretetype):
                cats = [output_categories[i] for output_categories in values]
                assert None not in cats
                newcats.append(min(cats))
            else:
                newcats.append(None)
        if newcats != self.inputargs_category:
            self.inputargs_category = newcats
            return True
        else:
            return False


    def patch_now(self):
        if self.patch is None:
            return
        newoperations, switchv, linkoperations = self.patch
        self.block.operations = newoperations
        if switchv is not None:
            self.block.exitswitch = switchv
        assert len(linkoperations) == len(self.block.exits)
        for link, (newargs, newoperations, _) in zip(self.block.exits,
                                                     linkoperations):
            link.args[:] = newargs
            if newoperations:
                # must put them in a fresh block along the link
                annotator = self.stmtransformer.translator.annotator
                newblock = insert_empty_block(annotator, link,
                                              newoperations)


def insert_stm_barrier(stmtransformer, graph):
    """This function uses the following characters for 'categories':

           * 'A': any general pointer
           * 'I': not a stub (immut_read_barrier was applied)
           * 'Q': same as R, except needs a repeat_read_barrier
           * 'R': the read barrier was applied
           * 'V': same as W, except needs a repeat_write_barrier
           * 'W': the write barrier was applied
           * 'Z': the null constant

       The letters are chosen so that a barrier is needed to change a
       pointer from category x to category y if and only if y > x.
    """
    join_blocks(graph)
    graphinfo = stmtransformer.write_analyzer.compute_graph_info(graph)
    annotator = stmtransformer.translator.annotator
    insert_empty_startblock(annotator, graph)

    block_transformers = {}

    for block in graph.iterblocks():
        if block.operations == ():
            continue
        bt = BlockTransformer(stmtransformer, block)
        bt.analyze_inside_block(graph)
        block_transformers[block] = bt

    bt = block_transformers[graph.startblock]
    bt.init_start_block()
    pending = set([bt])

    while pending:
        bt = pending.pop()
        bt.flow_through_block(graphinfo)
        pending |= bt.update_targets(block_transformers)

    for bt in block_transformers.values():
        bt.patch_now()
