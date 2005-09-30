from pypy.objspace.flow.model import Block, flatten, SpaceOperation, Constant, Variable
from pypy.rpython.lltype import Struct, GcStruct, Void, Ptr


def merge_mallocs(translator, graph):
    """Merge all mallocs of identical in a block into one.
    Thus all mallocs of atomic data are merged and all mallocs of
    non-atomic data are also merged into one. This reasoning behind this is
    that data allocated in the same block will probably have about the same
    livespan. So we hope that this does not increase the memory appetite
    of your program by much.

    warning: some will consider this a dirty hack, that's ok! :)
    """
    n_times_merged = 0
    blocks = [x for x in flatten(graph) if isinstance(x, Block)]
    for block in blocks:
        mallocs = [[], []]
        for i, op in enumerate(block.operations):
            if op.opname == 'malloc' and op.args[0].value._arrayfld:
                print 'merge_mallocs: skip varsize', op.args[0]
            if op.opname != 'malloc' or op.args[0].value._arrayfld:
                continue
            is_atomic = op.args[0].value._is_atomic()
            mallocs[is_atomic].append( (i,op.args[0].value) )

        for a in range(2):
            if len(mallocs[a]) >= 2:
                indices     = [m[0] for m in mallocs[a]]
                gcstructs   = [m[1] for m in mallocs[a]]
                merged_name = 'mergedstructs__' + '_'.join([s._name+str(n) for n, s in enumerate(gcstructs)])

                x = [(gcstruct._name+str(n), gcstruct) for n, gcstruct in enumerate(gcstructs)]
                mergedstruct= GcStruct(merged_name, *x)
                c = Constant(mergedstruct, Void)
                ptr_merged = Variable('ptr_mergedstructs')
                ptr_merged.concretetype = Ptr(c.value)
                merged_op  = SpaceOperation('malloc', [c], ptr_merged)
                block.operations.insert(0, merged_op)

                for n, i in enumerate(indices):
                    op = block.operations[i+1]
                    field = Constant(x[n][0], Void)
                    block.operations[i+1] = SpaceOperation('getsubstruct', [ptr_merged, field], op.result)

                for m in mallocs[a]:
                    index, type_ = m
                    print 'merge_malloc: OLD %d, %s' % (index, type(type_))
                print 'merge_mallocs: NEW %s, %s' % (c, c.concretetype)
                n_times_merged += 1

    return n_times_merged
