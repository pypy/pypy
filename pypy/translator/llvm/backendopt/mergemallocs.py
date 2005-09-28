from pypy.objspace.flow.model import Block, flatten, SpaceOperation


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
        n_mallocs_in_block = 0
        for op in block.operations:
            if op.opname != 'malloc':
                continue
            n_mallocs_in_block += 1
        if n_mallocs_in_block >= 2:
            print 'merge_mallocs: n_mallocs_in_block=%d' % n_mallocs_in_block
            n_times_merged += 1
    return n_times_merged
