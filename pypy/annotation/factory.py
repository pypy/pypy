"""
Mutable Objects Factories.

A factory is associated to an SpaceOperation in the source that creates a
built-in mutable object: currently 'newlist' and 'newdict'.
The factory remembers how general an object it has to create here.
"""

from pypy.annotation.model import SomeList, SomeDict
from pypy.annotation.model import SomeImpossibleValue, unionof
from pypy.annotation.bookkeeper import getbookkeeper


class BlockedInference(Exception):
    """This exception signals the type inference engine that the situation
    is currently blocked, and that it should try to progress elsewhere."""

    def __init__(self):
        try:
            self.break_at = getbookkeeper().position_key
        except AttributeError:
            self.break_at = None

    def __repr__(self):
        return "<BlockedInference break_at %r>" %(self.break_at,)
    __str__ = __repr__


class ListFactory:
    s_item = SomeImpossibleValue()

    def __repr__(self):
        return '%s(s_item=%r)' % (self.__class__.__name__, self.s_item)

    def create(self):
        return SomeList(factories = {self: True}, s_item = self.s_item)

    def generalize(self, s_new_item):
        if not self.s_item.contains(s_new_item):
            self.s_item = unionof(self.s_item, s_new_item)
            return True
        else:
            return False


class DictFactory:
    items = {}

    def __repr__(self):
        return '%s(items=%r)' % (self.__class__.__name__, self.items)

    def create(self):
        return SomeDict(factories = {self: True}, items = self.items)

    def generalize(self, key, s_new_value):
        self.items = self.items.copy()
        if key not in self.items:
            self.items[key] = s_new_value
            return True
        elif not self.items[key].contains(s_new_value):
            self.items[key] = unionof(self.items[key], s_new_value)
            return True
        else:
            return False


def generalize(factories, *args):
    """Signals all the factories in the given set to generalize themselves.
    The args must match the signature of the generalize() method of the
    particular factories (which should all be of the same class).
    """
    modified = [factory for factory in factories if factory.generalize(*args)]
    if modified:
        for factory in modified:
            factory.bookkeeper.annotator.reflowfromposition(factory.position_key)
        raise BlockedInference   # reflow now
