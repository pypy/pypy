from rpython.flowspace.model import SpaceOperation, Constant, Variable
from rpython.translator.unsimplify import varoftype, insert_empty_block, insert_empty_startblock
from rpython.rtyper.lltypesystem import lltype
from rpython.translator.stm.support import is_immutable
from rpython.translator.simplify import join_blocks

MALLOCS = set([
    'malloc', 'malloc_varsize',
    'malloc_nonmovable', 'malloc_nonmovable_varsize',
    'malloc_noconflict', 'malloc_noconflict_varsize',
    ])
READ_OPS = set(['getfield', 'getarrayitem', 'getinteriorfield', 'raw_load'])




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
        # all input args have category "any"
        from_outside = ['A'] * len(self.block.inputargs)
        self.inputargs_category_per_link[None] = from_outside
        self.update_inputargs_category()


    def analyze_inside_block(self, graph):
        gcremovetypeptr = self.stmtransformer.translator.config.translation.gcremovetypeptr

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
            elif ((op.opname in ('getarraysize', 'getinteriorarraysize') and
                   is_gc_ptr(op.args[0].concretetype)) or
                  (is_getter and is_immutable(op))):
                # immutable getters
                pass
            elif is_getter:
                if not stm_ignored:
                    wants_a_barrier[op] = 'R'
            elif op.opname == 'weakref_deref':
                # 'weakref_deref': kind of immutable, but the GC has to see
                #     which transactions read from a dying weakref, so we
                #     need the barrier nonetheless...
                wants_a_barrier[op] = 'R'
            elif op.opname == 'stm_ignored_start':
                assert not stm_ignored, "nested 'with stm_ignored'"
                stm_ignored = True
            elif op.opname == 'stm_ignored_stop':
                assert stm_ignored, "stm_ignored_stop without start?"
                stm_ignored = False

            if stm_ignored and op in wants_a_barrier:
                assert wants_a_barrier[op] == 'R'
                if is_getter and is_gc_ptr(op.result.concretetype):
                    raise Exception(
                        "%r: 'with stm_ignored:' contains unsupported "
                        "operation %r reading a GC pointer" % (graph, op))
        #
        if stm_ignored:
            raise Exception("%r: 'with stm_ignored:' code body too complex"
                            % (graph,))
        self.wants_a_barrier = wants_a_barrier


    def flow_through_block(self):

        def catfetch(v):
            return cat_map.setdefault(v, 'A')

        def get_category_or_null(v):
            # 'v' is an original variable here, or a constant
            if isinstance(v, Constant) and not v.value:    # a NULL constant
                return 'Z'
            if v in cat_map:
                return cat_map[v]
            if isinstance(v, Constant):
                return 'R'
            else:
                return 'A'


        cat_map = {} # var: category
        newoperations = []
        stmtransformer = self.stmtransformer

        # make the initial trivial renamings needed to have some precise
        # categories for the input args
        for v, cat in zip(self.block.inputargs, self.inputargs_category):
            if is_gc_ptr(v.concretetype):
                assert cat is not None
                cat_map[v] = cat

        for op in self.block.operations:
            #
            if (op.opname in ('cast_pointer', 'same_as') and
                    is_gc_ptr(op.result.concretetype)):
                cat_map[op.result] = catfetch(op.args[0])
                assert not self.wants_a_barrier.get(op)
            #
            to = self.wants_a_barrier.get(op)
            if to is not None:
                var = op.args[0]
                frm = catfetch(op.args[0])
                if needs_barrier(frm, to):
                    stmtransformer.read_barrier_counts += 1
                    v_none = varoftype(lltype.Void)
                    newoperations.append(
                        SpaceOperation('stm_read', [var], v_none))
                    cat_map[var] = to
            #
            newoperations.append(op)
            #
            if (stmtransformer.break_analyzer.analyze(op)
                or op.opname == 'debug_stm_flush_barrier'):
                # this operation can perform a transaction break:
                # all pointers are lowered to 'A'
                for v in cat_map.keys():
                    cat_map[v] = 'A'
            #
            if op.opname in MALLOCS:
                assert op.result not in cat_map
                cat_map[op.result] = 'R'
            #
            if op.opname == 'stm_read':
                # explicit or inserted by stmframework.py
                cat_map[op.args[0]] = 'R'
            elif op.opname in ('setfield', 'setarrayitem', 'setinteriorfield',
                             'raw_store', 'gc_writebarrier'):
                # compare with logic in stmframework.py
                # ops that need a write barrier also make the var 'R'
                if (op.args[-1].concretetype is not lltype.Void
                    and is_gc_ptr(op.args[0].concretetype)):
                    cat_map[op.args[0]] = 'R'

        if isinstance(self.block.exitswitch, Variable):
            switchv = self.block.exitswitch
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
            linkoperations.append((newoperations, output_categories))
        #
        # Record how we'd like to patch the block, but don't do any
        # patching yet
        self.patch = (blockoperations, switchv, linkoperations)


    def update_targets(self, block_transformers):
        (_, _, linkoperations) = self.patch
        assert len(linkoperations) == len(self.block.exits)
        targetbts = []
        for link, (_, output_categories) in zip(self.block.exits,
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
        for link, (newoperations, _) in zip(self.block.exits,
                                                     linkoperations):
            if newoperations:
                # must put them in a fresh block along the link
                annotator = self.stmtransformer.translator.annotator
                newblock = insert_empty_block(annotator, link,
                                              newoperations)


def insert_stm_read_barrier(stmtransformer, graph):
    """This function uses the following characters for 'categories':

           * 'A': any general pointer
           * 'R': the read (or write) barrier was applied
           * 'Z': the null constant

       The letters are chosen so that a barrier is needed to change a
       pointer from category x to category y if and only if y > x.
    """
    # We need to put enough 'stm_read' in the graph so that any
    # execution of a READ_OP on some GC object is guaranteed to also
    # execute either 'stm_read' or 'stm_write' on the same GC object
    # during the same transaction.

    join_blocks(graph)
    annotator = stmtransformer.translator.annotator
    insert_empty_startblock(graph)

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
