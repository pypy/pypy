from pypy.objspace.std.model import W_Object
from pypy.rlib.objectmodel import specialize


class Mixin_BaseStringMethods(object):
    __slots__ = ()

    def isalnum(w_self, space):
        return w_self._all_true(space, w_self._isalnum)

    def isalpha(w_self, space):
        return w_self._all_true(space, w_self._isalpha)

    def isdigit(w_self, space):
        return w_self._all_true(space, w_self._isdigit)

    def islower(w_self, space):
        return w_self._none_false_one_true(space,
                w_self._islower, w_self._isupper)

    def isspace(w_self, space):
        return w_self._all_true(space, w_self._isspace)

    def isupper(w_self, space):
        return w_self._none_false_one_true(space,
                w_self._isupper, w_self._islower)

    def istitle(w_self, space):
        return w_self._title(space)

    def lower(w_self, space):
        return w_self._transform(space, w_self._lower)

    def swapcase(w_self, space):
        return w_self._transform(space, w_self._swapcase)

    def upper(w_self, space):
        return w_self._transform(space, w_self._upper)


class AbstractCharIterator(object):

    def __init__(self, sequence):
        self.sequence = sequence
        self.pos = 0

    def __len__(self):
        return len(self.sequence)

    def __iter__(self):
        return self

    def next(self):
        ch = self.nextchar()
        if ch is None:
            raise StopIteration
        return ch

    # XXX deprecate nextchar() method
    def nextchar(self):
        if self.pos >= len(self):
            return None
        idx = self.pos
        self.pos += 1
        return self.sequence[idx]


class W_AbstractBaseStringObject(W_Object):
    __slots__ = ()

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%r)" % (w_self.__class__.__name__, w_self.raw_value())

    def builder(w_self, space, size=0):
        raise NotImplemented, "method not implemented"

    def construct(w_self, space, data):
        raise NotImplemented, "method not implemented"

    def immutable_unique_id(w_self, space):
        if w_self.user_overridden_class:
            return None
        return space.wrap(compute_unique_id(w_self.unwrap(space)))

    def is_w(self, space, w_other):
        if not isinstance(w_other, W_AbstractBaseStringObject):
            return False
        if self is w_other:
            return True
        if self.user_overridden_class or w_other.user_overridden_class:
            return False
        return self.unwrap(space) is w_other.unwrap(space)

    def iterator(w_self, space):
        return AbstractCharIterator(w_self.unwrap(space))

    def length(w_self, space):
        return len(w_self.unwrap(space))

    def raw_value(w_self):
        raise NotImplemented, "method not implemented"

    def str_w(w_self, space):
        raise NotImplemented, "method not implemented"

    def unicode_w(w_self, space):
        raise NotImplemented, "method not implemented"

    def unwrap(w_self, space):
        raise NotImplemented, "method not implemented"

    @specialize.arg(2)
    def _all_true(w_self, space, func):
        """Test all elements of a list with func for True.
        Returns True only if all elements test True."""
        size = w_self.length(space)
        it = w_self.iterator(space)
        if size == 0:
            return space.w_False
        if size == 1:
            return space.newbool(func(it.nextchar()))
        # not all it objects will support iterator protocol, eg rope
        for pos in range(size):
            ch = it.nextchar()
            if not func(ch):
                return space.w_False
        return space.w_True

    @specialize.arg(2, 3)
    def _none_false_one_true(w_self, space, pred, inverse):
        """Test all elements against predicate and inverse.
        Returns True only if all elements fail inverse and at least one
        element passes predicate."""
        v = w_self.unwrap(space)
        if len(v) == 1:
            c = v[0]
            return space.newbool(pred(c))
        status = False
        for idx in range(len(v)):
            if inverse(v[idx]):
                return space.w_False
            elif not status and pred(v[idx]):
                status = True
        return space.newbool(status)

    def _title(w_self, space):
        input = w_self.unwrap(space)
        cased = False
        previous_is_cased = False

        for pos in range(0, len(input)):
            ch = input[pos]
            if w_self._isupper(ch):
                if previous_is_cased:
                    return space.w_False
                previous_is_cased = True
                cased = True
            elif w_self._islower(ch):
                if not previous_is_cased:
                    return space.w_False
                cased = True
            else:
                previous_is_cased = False

        return space.newbool(cased)

    @specialize.arg(2)
    def _transform(w_self, space, func):
        sz = w_self.length(space)
        it = w_self.iterator(space)
        bd = w_self.builder(space, sz)
        for pos in range(sz):
            ch = it.nextchar()
            bd.append(func(ch))
        return w_self.construct(space, bd.build())
