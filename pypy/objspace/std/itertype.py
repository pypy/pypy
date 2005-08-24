from pypy.objspace.std.stdtypedef import *

# ____________________________________________________________
iter_typedef = StdTypeDef("sequenceiterator",
    __doc__ = '''iter(collection) -> iterator
iter(callable, sentinel) -> iterator

Get an iterator from an object.  In the first form, the argument must
supply its own iterator, or be a sequence.
In the second form, the callable is called until it returns the sentinel.'''
    )

reverse_iter_typedef = StdTypeDef("reversesequenceiterator",
    )
