from pypy.interpreter import gateway
from pypy.objspace.std.stdtypedef import StdTypeDef
from pypy.interpreter.error import OperationError

# ____________________________________________________________

def descr_seqiter__reduce__(w_self, space):
    """
    XXX to do: remove this __reduce__ method and do
    a registration with copy_reg, instead.
    """

    # cpython does not support pickling iterators but stackless python do
    #msg = 'Pickling for iterators dissabled as cpython does not support it'
    #raise OperationError(space.w_TypeError, space.wrap(msg))

    from pypy.objspace.std.iterobject import W_AbstractSeqIterObject
    assert isinstance(w_self, W_AbstractSeqIterObject)
    from pypy.interpreter.mixedmodule import MixedModule
    w_mod    = space.getbuiltinmodule('_pickle_support')
    mod      = space.interp_w(MixedModule, w_mod)
    new_inst = mod.get('seqiter_new')
    tup      = [w_self.w_seq, space.wrap(w_self.index)]
    return space.newtuple([new_inst, space.newtuple(tup)])


def descr_seqiter__length_hint__(space, w_self):
    from pypy.objspace.std.iterobject import W_AbstractSeqIterObject
    assert isinstance(w_self, W_AbstractSeqIterObject)
    return w_self.getlength(space)

# ____________________________________________________________

def descr_reverseseqiter__reduce__(w_self, space):
    """
    XXX to do: remove this __reduce__ method and do
    a registration with copy_reg, instead.
    """
    from pypy.objspace.std.iterobject import W_ReverseSeqIterObject
    assert isinstance(w_self, W_ReverseSeqIterObject)
    from pypy.interpreter.mixedmodule import MixedModule
    w_mod    = space.getbuiltinmodule('_pickle_support')
    mod      = space.interp_w(MixedModule, w_mod)
    new_inst = mod.get('reverseseqiter_new')
    tup      = [w_self.w_seq, space.wrap(w_self.index)]
    return space.newtuple([new_inst, space.newtuple(tup)])


def descr_reverseseqiter__length_hint__(space, w_self):
    from pypy.objspace.std.iterobject import W_ReverseSeqIterObject
    assert isinstance(w_self, W_ReverseSeqIterObject)
    if w_self.w_seq is None:
        return space.wrap(0)
    index = w_self.index + 1
    w_length = space.len(w_self.w_seq)
    # if length of sequence is less than index :exhaust iterator
    if space.is_true(space.gt(space.wrap(w_self.index), w_length)):
        w_len = space.wrap(0)
        w_self.w_seq = None
    else:
        w_len = space.wrap(index)
    if space.is_true(space.lt(w_len, space.wrap(0))):
        w_len = space.wrap(0)
    return w_len

# ____________________________________________________________
iter_typedef = StdTypeDef("sequenceiterator",
    __doc__ = '''iter(collection) -> iterator
iter(callable, sentinel) -> iterator

Get an iterator from an object.  In the first form, the argument must
supply its own iterator, or be a sequence.
In the second form, the callable is called until it returns the sentinel.''',

    __reduce__ = gateway.interp2app(descr_seqiter__reduce__),
    __length_hint__ = gateway.interp2app(descr_seqiter__length_hint__),
    )
iter_typedef.acceptable_as_base_class = False

reverse_iter_typedef = StdTypeDef("reversesequenceiterator",

    __reduce__ = gateway.interp2app(descr_reverseseqiter__reduce__),
    __length_hint__ = gateway.interp2app(descr_reverseseqiter__length_hint__),
    )
reverse_iter_typedef.acceptable_as_base_class = False
