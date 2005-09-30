from pypy.objspace.flow.model import Block, Constant, flatten, SpaceOperation
from pypy.translator.backendopt.inline import _find_exception_type


def remove_exception_mallocs(translator, graph):
    """Remove mallocs that occur because an exception is raised.
    Typically this data is shortlived and occuring often in highlevel
    languages like Python. So it would be preferable if we would not need
    to call a malloc function. We can not allocate the data on the stack
    because a global pointer (last_exception_type) is pointing to it.

    Here we use a ringbuffer of fixed size to contain exception instances.
    Our ringbuffer entries have fixed (maximum)size so all malloc over that
    amount are not affected by this code.
    
    warning: this code will not work when your code references
             an exception instance 'long' after it has been raised.
    """
    n_removed = 0
    blocks = [x for x in flatten(graph) if isinstance(x, Block)]
    for block in blocks:
        ops = block.operations
        if len(ops) < 3 or \
           ops[0].opname != 'malloc'   or ops[1].opname != 'cast_pointer'   or \
           ops[2].opname != 'setfield' or ops[2].args[1].value != 'typeptr' or \
           not isinstance(ops[2].args[1], Constant):
            continue
        name = str(ops[0].args[0])
        if 'Exception' not in name and 'Error' not in name: #XXX better to look at the actual structure
            continue
        print 'remove_exception_malloc: ', name
        ops[0].opname = 'malloc_exception'  #XXX refactor later to not use a new operationtype
        n_removed += 1
    return n_removed
