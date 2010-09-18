# NOT_RPYTHON

import gc

def dump_rpy_heap(file):
    """Write a full dump of the objects in the heap to the given file
    (which can be a file, a file name, or a file descritor).
    Format for each object (each item is one machine word):

        [addr] [typeindex] [size] [addr1]..[addrn] [-1]

    where [addr] is the address of the object, [typeindex] and [size]
    are as get_rpy_type_index() and get_rpy_memory_usage() would return,
    and [addr1]..[addrn] are addresses of other objects that this object
    points to.  The full dump is a list of such objects, with a marker
    [0][0][0][-1] inserted after all GC roots, before all non-roots.
    """
    if isinstance(file, str):
        f = open(file, 'wb')
        gc._dump_rpy_heap(f.fileno())
        f.close()
    else:
        if isinstance(file, int):
            fd = file
        else:
            if hasattr(file, 'flush'):
                file.flush()
            fd = file.fileno()
        gc._dump_rpy_heap(fd)
