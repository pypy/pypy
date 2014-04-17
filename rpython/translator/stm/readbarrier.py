from rpython.flowspace.model import SpaceOperation, Constant, Variable
from rpython.rtyper.lltypesystem import lltype
from rpython.translator.unsimplify import varoftype, insert_empty_block
from rpython.translator.unsimplify import insert_empty_startblock
from rpython.translator.simplify import join_blocks


MALLOCS = set([
    'malloc', 'malloc_varsize',
    'malloc_nonmovable', 'malloc_nonmovable_varsize',
    ])

READ_OPS = set(['getfield', 'getarrayitem', 'getinteriorfield', 'raw_load'])

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
        stm_ignored = False
        for op in self.block.operations:
            is_getter = (op.opname in READ_OPS and
                         op.result.concretetype is not lltype.Void and
                         is_gc_ptr(op.args[0].concretetype))

            if (gcremovetypeptr and op.opname in ('getfield', 'setfield') and
                op.args[1].value == 'typeptr' and
                op.args[0].concretetype.TO._hints.get('typeptr')):
                # typeptr is always immutable
                pass
            elif (op.opname in ('getarraysize', 'getinteriorarraysize') and
                  is_gc_ptr(op.args[0].concretetype) or
                  (is_getter and is_immutable(op))):
                # immutable getters
                pass
            elif is_getter:
                # the non-immutable getfields need a regular read barrier
                if not stm_ignored:
                    wants_a_barrier[op] = 'R'
            elif op.opname == 'weakref_deref':
                # 'weakref_deref' needs a read barrier if we want to work
                # around the "weakref issue"
                assert not stm_ignored
                wants_a_barrier[op] = 'R'
            elif op.opname == 'stm_ignored_start':
                assert not stm_ignored, "nested 'with stm_ignored'"
                stm_ignored = True
            elif op.opname == 'stm_ignored_stop':
                assert stm_ignored, "stm_ignored_stop without start?"
                stm_ignored = False
        #
        if stm_ignored:
            raise Exception("%r: 'with stm_ignored:' code body too complex"
                            % (graph,))
        self.wants_a_barrier = wants_a_barrier


    def flow_through_block(self):
        def cat_fetch(v):
            return categories.setdefault(v, 'A')

        def get_category_or_null(v):
            # 'v' is an original variable here, or a constant
            if isinstance(v, Constant) and not v.value:    # a NULL constant
                return 'Z'
            if v in categories:
                return categories[v]
            return 'A'

        newoperations = []
        stmtransformer = self.stmtransformer
        categories = {}

        # make the initial trivial renamings needed to have some precise
        # categories for the input args
        for v, cat in zip(self.block.inputargs, self.inputargs_category):
            if is_gc_ptr(v.concretetype):
                assert cat is not None
                categories[v] = cat

        for op in self.block.operations:
            if (op.opname in ('cast_pointer', 'same_as') and
                    is_gc_ptr(op.result.concretetype)):
                categories[op.result] = cat_fetch(op.args[0])
                newoperations.append(op)
                continue
            #
            to = self.wants_a_barrier.get(op)
            if to is not None:
                v = op.args[0]
                frm = cat_fetch(v)
                if needs_barrier(frm, to):
                    stmtransformer.read_barrier_counts += 1
                    v_none = varoftype(lltype.Void)
                    newop = SpaceOperation('stm_read', [v], v_none)
                    categories[v] = to
                    newoperations.append(newop)
            #
            newoperations.append(op)
            #
            if stmtransformer.break_analyzer.analyze(op):
                # this operation can perform a transaction break:
                # all references are lowered to 'A' again
                for v in categories:
                    categories[v] = 'A'

            if op.opname == 'debug_stm_flush_barrier':
                for v in categories:
                    categories[v] = 'A'

            if op.opname in MALLOCS:
                categories[op.result] = 'R'

        blockoperations = newoperations
        linkoperations = []
        for link in self.block.exits:
            output_categories = []
            for v in link.args:
                if is_gc_ptr(v.concretetype):
                    cat = cat_fetch(v)
                else:
                    cat = None
                output_categories.append(cat)
            linkoperations.append(output_categories)
        #
        # Record how we'd like to patch the block, but don't do any
        # patching yet
        self.patch = (blockoperations, linkoperations)


    def update_targets(self, block_transformers):
        (_, linkoperations) = self.patch
        assert len(linkoperations) == len(self.block.exits)
        targetbts = []
        for link, output_categories in zip(self.block.exits, linkoperations):
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
        newoperations, linkoperations = self.patch
        self.block.operations = newoperations
        assert len(linkoperations) == len(self.block.exits)
        # for link, (newargs, newoperations, _) in zip(self.block.exits,
        #                                              linkoperations):
        #     link.args[:] = newargs
        #     if newoperations:
        #         # must put them in a fresh block along the link
        #         annotator = self.stmtransformer.translator.annotator
        #         insert_empty_block(annotator, link, newoperations)


def insert_stm_read_barrier(stmtransformer, graph):
    """This function uses the following characters for 'categories':

           * 'A': any general pointer
           * 'R': the read barrier was applied
           * 'Z': the null constant

       The letters are chosen so that a barrier is needed to change a
       pointer from category x to category y if and only if y > x.
    """
    # XXX: we currently don't use the information that any write
    # operation on a gcptr will make it readable automatically
    join_blocks(graph)
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
        bt.flow_through_block()
        pending |= bt.update_targets(block_transformers)

    for bt in block_transformers.values():
        bt.patch_now()

    # needed only for some fragile test ztranslated.test_stm_ignored
    join_blocks(graph)
