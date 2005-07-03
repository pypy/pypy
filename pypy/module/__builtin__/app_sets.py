# NOT_RPYTHON
"""
This emulates CPython's set and frozenset types based on the current sets
module. Diff against the sets module to find specific changes. Here's some
pointers:

- __slots__ as well as __setstate__/__getstate__ were removed from the set
  classes to support pickling in conjunction with __reduce__.
- non-operator methods like (update, issubset, issuperset - see the set type
  documentation for a full list) now accept iterables in addition to just other
  sets.
- copy semantics for frozensets according to the frozenset type from CPython
- the hash algorithm for CPython's frozenset was not implemented because it
  relies on integer overflows.

This whole module should probably be converted to RPython at some point in the
future.

The following is the original docstring from sets.py:

Classes to represent arbitrary sets (including sets of sets).

This module implements sets using dictionaries whose values are
ignored.  The usual operations (union, intersection, deletion, etc.)
are provided as both methods and operators.

Important: sets are not sequences!  While they support 'x in s',
'len(s)', and 'for x in s', none of those operations are unique for
sequences; for example, mappings support all three as well.  The
characteristic operation for sequences is subscripting with small
integers: s[i], for i in range(len(s)).  Sets don't support
subscripting at all.  Also, sequences allow multiple occurrences and
their elements have a definite order; sets on the other hand don't
record multiple occurrences and don't remember the order of element
insertion (which is why they don't support s[i]).

The following classes are provided:

BaseSet -- All the operations common to both mutable and immutable
    sets. This is an abstract class, not meant to be directly
    instantiated.

set -- Mutable sets, subclass of BaseSet; not hashable.

frozenset -- Immutable sets, subclass of BaseSet; hashable.
    An iterable argument is mandatory to create an frozenset.

_TemporarilyImmutableSet -- A wrapper around a Set, hashable,
    giving the same hash value as the immutable set equivalent
    would have.  Do not use this class directly.

Only hashable objects can be added to a set. In particular, you cannot
really add a set as an element to another set; if you try, what is
actually added is an frozenset built from it (it compares equal to
the one you tried adding).

When you ask if `x in y' where x is a Set and y is a Set or
frozenset, x is wrapped into a _TemporarilyImmutableSet z, and
what's tested is actually `z in y'.

"""

# Code history:
#
# - Greg V. Wilson wrote the first version, using a different approach
#   to the mutable/immutable problem, and inheriting from dict.
#
# - Alex Martelli modified Greg's version to implement the current
#   Set/frozenset approach, and make the data an attribute.
#
# - Guido van Rossum rewrote much of the code, made some API changes,
#   and cleaned up the docstrings.
#
# - Raymond Hettinger added a number of speedups and other
#   improvements.

from __future__ import generators
try:
    from itertools import ifilter, ifilterfalse
except ImportError:
    # Code to make the module run under Py2.2
    def ifilter(predicate, iterable):
        if predicate is None:
            def predicate(x):
                return x
        for x in iterable:
            if predicate(x):
                yield x
    def ifilterfalse(predicate, iterable):
        if predicate is None:
            def predicate(x):
                return x
        for x in iterable:
            if not predicate(x):
                yield x
    try:
        True, False
    except NameError:
        True, False = (0==0, 0!=0)

__all__ = ['set', 'frozenset']

class BaseSet(object):
    """Common base class for mutable and immutable sets."""

    # Constructor

    def __init__(self):
        """This is an abstract class."""
        # Don't call this from a concrete subclass!
        if self.__class__ is BaseSet:
            raise TypeError, ("BaseSet is an abstract class.  "
                              "Use set or frozenset.")

    # Standard protocols: __len__, __repr__, __str__, __iter__, __reduce__

    def __len__(self):
        """Return the number of elements of a set."""
        return len(self._data)

    def __repr__(self):
        """Return string representation of a set.

        This looks like 'set([<list of elements>])'.
        """
        return self._repr()

    # __str__ is the same as __repr__
    __str__ = __repr__

    def _repr(self, sorted=False):
        elements = self._data.keys()
        if sorted:
            elements.sort()
        return '%s(%r)' % (self.__class__.__name__, elements)

    def __iter__(self):
        """Return an iterator over the elements or a set.

        This is the keys iterator for the underlying dict.
        """
        return self._data.iterkeys()

    def __reduce__(self):
        return (self.__class__, (self._data.keys(),), self.__dict__)

    # Three-way comparison is not supported.  However, because __eq__ is
    # tried before __cmp__, if set x == set y, x.__eq__(y) returns True and
    # then cmp(x, y) returns 0 (Python doesn't actually call __cmp__ in this
    # case).

    def __cmp__(self, other):
        raise TypeError, "can't compare sets using cmp()"

    # Equality comparisons using the underlying dicts.  Mixed-type comparisons
    # are allowed here, where set == z for non-set z always returns False,
    # and set != z always True.  This allows expressions like "x in y" to
    # give the expected result when y is a sequence of mixed types, not
    # raising a pointless TypeError just because y contains a set, or x is
    # a set and y contain's a non-set ("in" invokes only __eq__).
    # Subtle:  it would be nicer if __eq__ and __ne__ could return
    # NotImplemented instead of True or False.  Then the other comparand
    # would get a chance to determine the result, and if the other comparand
    # also returned NotImplemented then it would fall back to object address
    # comparison (which would always return False for __eq__ and always
    # True for __ne__).  However, that doesn't work, because this type
    # *also* implements __cmp__:  if, e.g., __eq__ returns NotImplemented,
    # Python tries __cmp__ next, and the __cmp__ here then raises TypeError.

    def __eq__(self, other):
        if isinstance(other, BaseSet):
            return self._data == other._data
        else:
            return False

    def __ne__(self, other):
        if isinstance(other, BaseSet):
            return self._data != other._data
        else:
            return True

    # Copying operations

    def copy(self):
        """Return a shallow copy of a set."""
        result = self.__class__()
        result._data.update(self._data)
        return result

    __copy__ = copy # For the copy module

    def __deepcopy__(self, memo):
        """Return a deep copy of a set; used by copy module."""
        # This pre-creates the result and inserts it in the memo
        # early, in case the deep copy recurses into another reference
        # to this same set.  A set can't be an element of itself, but
        # it can certainly contain an object that has a reference to
        # itself.
        from copy import deepcopy
        result = self.__class__()
        memo[id(self)] = result
        data = result._data
        value = True
        for elt in self:
            data[deepcopy(elt, memo)] = value
        return result

    # Standard set operations: union, intersection, both differences.
    # Each has an operator version (e.g. __or__, invoked with |) and a
    # method version (e.g. union).
    # Subtle:  Each pair requires distinct code so that the outcome is
    # correct when the type of other isn't suitable.  For example, if
    # we did "union = __or__" instead, then set().union(3) would return
    # NotImplemented instead of raising TypeError (albeit that *why* it
    # raises TypeError as-is is also a bit subtle).

    def __or__(self, other):
        """Return the union of two sets as a new set.

        (I.e. all elements that are in either set.)
        """
        if not isinstance(other, BaseSet):
            return NotImplemented
        return self.union(other)

    def union(self, other):
        """Return the union of two sets as a new set.

        (I.e. all elements that are in either set.)
        """
        result = self.__class__(self)
        result._update(other)
        return result

    def __and__(self, other):
        """Return the intersection of two sets as a new set.

        (I.e. all elements that are in both sets.)
        """
        if not isinstance(other, BaseSet):
            return NotImplemented
        return self.intersection(other)

    def intersection(self, other):
        """Return the intersection of two sets as a new set.

        (I.e. all elements that are in both sets.)
        """
        if not isinstance(other, BaseSet):
            other = set(other)
        if len(self) <= len(other):
            little, big = self, other
        else:
            little, big = other, self
        common = ifilter(big._data.has_key, little)
        return self.__class__(common)

    def __xor__(self, other):
        """Return the symmetric difference of two sets as a new set.

        (I.e. all elements that are in exactly one of the sets.)
        """
        if not isinstance(other, BaseSet):
            return NotImplemented
        return self.symmetric_difference(other)

    def symmetric_difference(self, other):
        """Return the symmetric difference of two sets as a new set.

        (I.e. all elements that are in exactly one of the sets.)
        """
        result = self.__class__()
        data = result._data
        value = True
        selfdata = self._data
        try:
            otherdata = other._data
        except AttributeError:
            otherdata = set(other)._data
        for elt in ifilterfalse(otherdata.has_key, selfdata):
            data[elt] = value
        for elt in ifilterfalse(selfdata.has_key, otherdata):
            data[elt] = value
        return result

    def  __sub__(self, other):
        """Return the difference of two sets as a new set.

        (I.e. all elements that are in this set and not in the other.)
        """
        if not isinstance(other, BaseSet):
            return NotImplemented
        return self.difference(other)

    def difference(self, other):
        """Return the difference of two sets as a new set.

        (I.e. all elements that are in this set and not in the other.)
        """
        result = self.__class__()
        data = result._data
        try:
            otherdata = other._data
        except AttributeError:
            otherdata = set(other)._data
        value = True
        for elt in ifilterfalse(otherdata.has_key, self):
            data[elt] = value
        return result

    # Membership test

    def __contains__(self, element):
        """Report whether an element is a member of a set.

        (Called in response to the expression `element in self'.)
        """
        try:
            return element in self._data
        except TypeError:
            transform = getattr(element, "__as_temporarily_immutable__", None)
            if transform is None:
                raise # re-raise the TypeError exception we caught
            return transform() in self._data

    # Subset and superset test

    def issubset(self, other):
        """Report whether another set contains this set."""
        if not isinstance(other, BaseSet):
            # other is an iterable
            other = self.__class__(other)
        if len(self) > len(other):  # Fast check for obvious cases
            return False
        for elt in ifilterfalse(other._data.has_key, self):
            return False
        return True

    def issuperset(self, other):
        """Report whether this set contains another set."""
        if not isinstance(other, BaseSet):
            # other is an iterable
            other = self.__class__(other)
        if len(self) < len(other):  # Fast check for obvious cases
            return False
        for elt in ifilterfalse(self._data.has_key, other):
            return False
        return True

    # Inequality comparisons using the is-subset relation.
    def __le__(self, other):
        self._binary_sanity_check(other)
        return self.issubset(other)
        
    def __ge__(self, other):
        self._binary_sanity_check(other)
        return self.issuperset(other)

    def __lt__(self, other):
        self._binary_sanity_check(other)
        return len(self) < len(other) and self.issubset(other)

    def __gt__(self, other):
        self._binary_sanity_check(other)
        return len(self) > len(other) and self.issuperset(other)

    # Assorted helpers

    def _binary_sanity_check(self, other):
        # Check that the other argument to a binary operation is also
        # a set, raising a TypeError otherwise.
        if not isinstance(other, BaseSet):
            raise TypeError, "Binary operation only permitted between sets"

    def _compute_hash(self):
        # Calculate hash code for a set by xor'ing the hash codes of
        # the elements.  This ensures that the hash code does not depend
        # on the order in which elements are added to the set.  This is
        # not called __hash__ because a BaseSet should not be hashable;
        # only an frozenset is hashable.
        result = 0
        for elt in self:
            result ^= hash(elt)
        return result

    def _update(self, iterable):
        # The main loop for update() and the subclass __init__() methods.
        data = self._data

        # Use the fast update() method when a dictionary is available.
        if isinstance(iterable, BaseSet):
            data.update(iterable._data)
            return

        value = True

        if type(iterable) in (list, tuple, xrange):
            # Optimized: we know that __iter__() and next() can't
            # raise TypeError, so we can move 'try:' out of the loop.
            it = iter(iterable)
            while True:
                try:
                    for element in it:
                        data[element] = value
                    return
                except TypeError:
                    transform = getattr(element, "__as_immutable__", None)
                    if transform is None:
                        raise # re-raise the TypeError exception we caught
                    data[transform()] = value
        else:
            # Safe: only catch TypeError where intended
            for element in iterable:
                try:
                    data[element] = value
                except TypeError:
                    transform = getattr(element, "__as_immutable__", None)
                    if transform is None:
                        raise # re-raise the TypeError exception we caught
                    data[transform()] = value


class frozenset(BaseSet):
    """Immutable set class."""

    # BaseSet + hashing

    def __new__(cls, iterable=None):
        if type(iterable) is frozenset:
            return iterable
        instance = BaseSet.__new__(cls)
        frozenset._init(instance, iterable)
        return instance

    def __init__(self, iterable=None):
        pass

    def _init(self, iterable=None):
        """Construct an immutable set from an optional iterable."""
        self._hashcode = None
        self._data = {}
        if iterable is not None:
            self._update(iterable)

    def __hash__(self):
        if self._hashcode is None:
            self._hashcode = self._compute_hash()
        return self._hashcode
    
    def union(self, other):
        return BaseSet.union(BaseSet.copy(self), other)

    def copy(self):
        if type(self) is frozenset:
            return self
        else:
            return self.__class__(self)

    __copy__ = copy

class set(BaseSet):
    """ Mutable set class."""

    # BaseSet + operations requiring mutability; no hashing

    def __init__(self, iterable=None):
        """Construct a set from an optional iterable."""
        self._data = {}
        if iterable is not None:
            self._update(iterable)

    def __hash__(self):
        """A set cannot be hashed."""
        # We inherit object.__hash__, so we must deny this explicitly
        raise TypeError, "Can't hash a set, only an frozenset."

    # In-place union, intersection, differences.
    # Subtle:  The xyz_update() functions deliberately return None,
    # as do all mutating operations on built-in container types.
    # The __xyz__ spellings have to return self, though.

    def __ior__(self, other):
        """Update a set with the union of itself and another."""
        self._binary_sanity_check(other)
        self._data.update(other._data)
        return self

    def union_update(self, other):
        """Update a set with the union of itself and another."""
        self._update(other)

    def __iand__(self, other):
        """Update a set with the intersection of itself and another."""
        self._binary_sanity_check(other)
        self._data = (self & other)._data
        return self

    def intersection_update(self, other):
        """Update a set with the intersection of itself and another."""
        if isinstance(other, BaseSet):
            self &= other
        else:
            self._data = (self.intersection(other))._data

    def __ixor__(self, other):
        """Update a set with the symmetric difference of itself and another."""
        self._binary_sanity_check(other)
        self.symmetric_difference_update(other)
        return self

    def symmetric_difference_update(self, other):
        """Update a set with the symmetric difference of itself and another."""
        data = self._data
        value = True
        if not isinstance(other, BaseSet):
            other = set(other)
        for elt in other:
            if elt in data:
                del data[elt]
            else:
                data[elt] = value

    def __isub__(self, other):
        """Remove all elements of another set from this set."""
        self._binary_sanity_check(other)
        self.difference_update(other)
        return self

    def difference_update(self, other):
        """Remove all elements of another set from this set."""
        data = self._data
        if not isinstance(other, BaseSet):
            other = set(other)
        for elt in ifilter(data.has_key, other):
            del data[elt]

    # Python dict-like mass mutations: update, clear

    def update(self, iterable):
        """Add all values from an iterable (such as a list or file)."""
        self._update(iterable)

    def clear(self):
        """Remove all elements from this set."""
        self._data.clear()

    # Single-element mutations: add, remove, discard

    def add(self, element):
        """Add an element to a set.

        This has no effect if the element is already present.
        """
        try:
            self._data[element] = True
        except TypeError:
            transform = getattr(element, "__as_immutable__", None)
            if transform is None:
                raise # re-raise the TypeError exception we caught
            self._data[transform()] = True

    def remove(self, element):
        """Remove an element from a set; it must be a member.

        If the element is not a member, raise a KeyError.
        """
        try:
            del self._data[element]
        except TypeError:
            transform = getattr(element, "__as_temporarily_immutable__", None)
            if transform is None:
                raise # re-raise the TypeError exception we caught
            del self._data[transform()]

    def discard(self, element):
        """Remove an element from a set if it is a member.

        If the element is not a member, do nothing.
        """
        try:
            self.remove(element)
        except KeyError:
            pass

    def pop(self):
        """Remove and return an arbitrary set element."""
        return self._data.popitem()[0]

    def __as_immutable__(self):
        # Return a copy of self as an immutable set
        return frozenset(self)

    def __as_temporarily_immutable__(self):
        # Return self wrapped in a temporarily immutable set
        return _TemporarilyImmutableSet(self)


class _TemporarilyImmutableSet(BaseSet):
    # Wrap a mutable set as if it was temporarily immutable.
    # This only supplies hashing and equality comparisons.

    def __init__(self, set):
        self._set = set
        self._data = set._data  # Needed by frozenset.__eq__()

    def __hash__(self):
        return self._set._compute_hash()
