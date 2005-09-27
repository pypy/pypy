from pypy.objspace.flow.model import Block, Constant, flatten, SpaceOperation
from pypy.translator.backendopt.inline import _find_exception_type


def _llvm_structsize(struct):
    #XXX TODO take a save guess
    return 16

def remove_exception_mallocs(translator, graph, ringbuffer_entry_maxsize=16, ringbuffer_n_entries=1024):
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
    blocks = [x for x in flatten(graph) if isinstance(x, Block)]
    for block in blocks:
        ops = block.operations
        if (len(ops) < 3 or
            ops[0].opname != 'malloc'   or ops[1].opname != 'cast_pointer'   or
            ops[2].opname != 'setfield' or ops[2].args[1].value != 'typeptr' or
            not isinstance(ops[2].args[1], Constant) or
            _llvm_structsize(ops[0].args[0]) > ringbuffer_entry_maxsize): #todo: ops[2].args[2] to vtable
            continue
        print 'remove_exception_malloc: ', str(ops[0].args[0]), ops[2].args[2]
        #ops = [SpaceOperation('ops[0].result = load sbyte** %exception_ringbuffer'),
        #       SpaceOperation('%tmpptr.0 = add sbyte* ops[0].result, ringbuffer_entry_maxsize'),
        #       SpaceOperation('%tmpptr.1 = and sbyte* tmpptr.0, ~(ringbuffer_n_entries*ringbuffer_entry_maxsize)'),
        #       SpaceOperation('store sbyte* %tmpptr.1, sbyte** %exception_ringbuffer),
        #       ops[1:]]
