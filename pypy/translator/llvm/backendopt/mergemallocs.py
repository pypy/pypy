from pypy.objspace.flow.model import Block, flatten, SpaceOperation, Constant
from pypy.rpython.lltype import GcStruct, Void


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
            print 'merge_malloc: OLD %d, %s, %s, %s' % (i, type(op.args[0]), op.args[0], op.args[0].concretetype)
        for a in range(2):
            if len(mallocs[a]) >= 2:
                indices     = [m[0] for m in mallocs[a]]
                structs     = [m[1] for m in mallocs[a]]
                merged_name = 'merged'
                for m in mallocs[a]:
                    merged_name += '_' + m[1]._name
                merged = GcStruct(merged_name,
                                  ('field1', super(GcStruct, structs[0])),
                                  ('field2', super(GcStruct, structs[1]))
                                 )
                print 'merge_mallocs: %s {%s} [%s]' % (indices, structs, merged)
                c = Constant(merged, Void)
                print 'merge_malloc: NEW %s, %s' % (c, c.concretetype)
                block.operations[indices[0]].args[0] = c
                n_times_merged += 1
    return n_times_merged
