from rpython.flowspace.model import SpaceOperation, Constant, Variable
from rpython.translator.unsimplify import varoftype, insert_empty_block
from rpython.rtyper.lltypesystem import lltype
from rpython.translator.backendopt.writeanalyze import top_set


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
    raise AssertionError(op)

def needs_barrier(frm, to):
    return to > frm


def insert_stm_barrier(stmtransformer, graph):
    """This function uses the following characters for 'categories':

           * 'A': any general pointer
           * 'I': not a stub (immut_read_barrier was applied)
           * 'Q': same as R, except needs a repeat_read_barrier
           * 'R': the read barrier was applied
           * 'V': same as W, except needs a repeat_write_barrier
           * 'W': the write barrier was applied

       The letters are chosen so that a barrier is needed to change a
       pointer from category x to category y if and only if y > x.
    """
    graphinfo = stmtransformer.write_analyzer.compute_graph_info(graph)

    def get_category(v):
        return category.get(v, 'A')

    def get_category_or_null(v):
        if isinstance(v, Constant) and not v.value:
            return None
        return category.get(v, 'A')

    def renamings_get(v):
        if v not in renamings:
            return v
        v2 = renamings[v][0]
        if v2.concretetype == v.concretetype:
            return v2
        v3 = varoftype(v.concretetype)
        newoperations.append(SpaceOperation('cast_pointer', [v2], v3))
        return v3

    for block in graph.iterblocks():
        if block.operations == ():
            continue
        #
        wants_a_barrier = {}
        expand_comparison = set()
        for op in block.operations:
            is_getter = (op.opname in ('getfield', 'getarrayitem',
                                       'getinteriorfield') and
                         op.result.concretetype is not lltype.Void and
                         op.args[0].concretetype.TO._gckind == 'gc')
            if (op.opname in ('getarraysize', 'getinteriorarraysize')
                or (is_getter and is_immutable(op))):
                # we can't leave getarraysize or the immutable getfields
                # fully unmodified: we need at least immut_read_barrier
                # to detect stubs.
                wants_a_barrier[op] = 'I'

            elif is_getter:
                # the non-immutable getfields need a regular read barrier
                wants_a_barrier[op] = 'R'

            elif (op.opname in ('setfield', 'setarrayitem',
                                'setinteriorfield') and
                  op.args[-1].concretetype is not lltype.Void and
                  op.args[0].concretetype.TO._gckind == 'gc'):
                # setfields need a regular write barrier
                wants_a_barrier[op] = 'W'

            elif (op.opname in ('ptr_eq', 'ptr_ne') and
                  op.args[0].concretetype.TO._gckind == 'gc'):
                # GC pointer comparison might need special care
                expand_comparison.add(op)
        #
        if wants_a_barrier or expand_comparison:
            # note: 'renamings' maps old vars to new vars, but cast_pointers
            # are done lazily.  It means that the two vars may not have
            # exactly the same type.
            renamings = {}   # {original-var: [var-in-newoperations] (len 1)}
            category = {}    # {var-in-newoperations: LETTER}
            newoperations = []
            for op in block.operations:
                #
                if op.opname == 'cast_pointer':
                    v = op.args[0]
                    renamings[op.result] = renamings.setdefault(v, [v])
                    continue
                #
                to = wants_a_barrier.get(op)
                if to is not None:
                    v = op.args[0]
                    v_holder = renamings.setdefault(v, [v])
                    v = v_holder[0]
                    frm = get_category(v)
                    if needs_barrier(frm, to):
                        try:
                            b = stmtransformer.barrier_counts[frm, to]
                        except KeyError:
                            c_info = Constant('%s2%s' % (frm, to), lltype.Void)
                            b = [0, c_info]
                            stmtransformer.barrier_counts[frm, to] = b
                        b[0] += 1
                        c_info = b[1]
                        w = varoftype(v.concretetype)
                        newop = SpaceOperation('stm_barrier', [c_info, v], w)
                        newoperations.append(newop)
                        v_holder[0] = w
                        category[w] = to
                #
                newop = SpaceOperation(op.opname,
                                       [renamings_get(v) for v in op.args],
                                       op.result)
                newoperations.append(newop)
                #
                if op in expand_comparison:
                    cats = (get_category_or_null(newop.args[0]),
                            get_category_or_null(newop.args[1]))
                    if None not in cats and (cats[0] < 'V' or cats[1] < 'V'):
                        if newop.opname == 'ptr_ne':
                            v = varoftype(lltype.Bool)
                            negop = SpaceOperation('bool_not', [v],
                                                   newop.result)
                            newoperations.append(negop)
                            newop.result = v
                        newop.opname = 'stm_ptr_eq'

                if stmtransformer.collect_analyzer.analyze(op):
                    # this operation can collect: we bring all 'W'
                    # categories back to 'V', because we would need
                    # a repeat_write_barrier on them afterwards
                    for v, cat in category.items():
                        if cat == 'W':
                            category[v] = 'V'

                effectinfo = stmtransformer.write_analyzer.analyze(
                    op, graphinfo=graphinfo)
                if effectinfo:
                    if effectinfo is top_set:
                        # this operation can perform random writes: any
                        # 'R'-category object falls back to 'Q' because
                        # we would need a repeat_read_barrier()
                        for v, cat in category.items():
                            if cat == 'R':
                                category[v] = 'Q'
                    else:
                        # the same, but only on objects of the right types
                        types = set([entry[1] for entry in effectinfo])
                        for v in category.keys():
                            if v.concretetype in types and category[v] == 'R':
                                category[v] = 'Q'
                        # XXX this is likely not general enough: we need
                        # to consider 'types' or any base type

                if op.opname in MALLOCS:
                    category[op.result] = 'W'

            block.operations = newoperations
            #
            for link in block.exits:
                newoperations = []
                for i, v in enumerate(link.args):
                    link.args[i] = renamings_get(v)
                if newoperations:
                    # must put them in a fresh block along the link
                    annotator = stmtransformer.translator.annotator
                    newblock = insert_empty_block(annotator, link,
                                                  newoperations)
