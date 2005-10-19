from pypy.annotation.model import SomeObject, SomeImpossibleValue
from pypy.annotation.model import unionof, TLS, UnionError, isdegenerated


class ListItem:
    mutated = False    # True for lists mutated after creation
    resized = False    # True for lists resized after creation
    range_step = None  # the step -- only for lists only created by a range()

    # what to do if range_step is different in merge.
    # - if one is a list (range_step is None), unify to a list.
    # - if both have a step, unify to use a variable step (indicated by 0)
    _step_map = {
        (type(None), int): None,
        (int, type(None)): None,
        (int, int)       : 0,
        }

    def __init__(self, bookkeeper, s_value):
        self.s_value = s_value
        self.bookkeeper = bookkeeper
        self.itemof = {}  # set of all ListDefs using this ListItem
        self.read_locations = {}

    def merge(self, other):
        if self is not other:
            if getattr(TLS, 'no_side_effects_in_union', 0):
                raise UnionError("merging list/dict items")
            self.mutated |= other.mutated
            self.resized |= other.resized
            if other.range_step != self.range_step:
                self.range_step = self._step_map[type(self.range_step),
                                                 type(other.range_step)]
            self.itemof.update(other.itemof)
            read_locations = self.read_locations.copy()
            other_read_locations = other.read_locations.copy()
            self.read_locations.update(other.read_locations)
            self.patch()    # which should patch all refs to 'other'
            s_value = self.s_value
            s_other_value = other.s_value
            s_new_value = unionof(s_value, s_other_value)
            if isdegenerated(s_new_value) and self.bookkeeper:
                self.bookkeeper.ondegenerated(self, s_new_value)
            if s_new_value != s_value:
                self.s_value = s_new_value
                # reflow from reading points
                for position_key in read_locations:
                    self.bookkeeper.annotator.reflowfromposition(position_key) 
            if s_new_value != s_other_value:
                # reflow from reading points
                for position_key in other_read_locations:
                    self.bookkeeper.annotator.reflowfromposition(position_key) 

    def patch(self):
        for listdef in self.itemof:
            listdef.listitem = self

    def generalize(self, s_other_value):
        s_new_value = unionof(self.s_value, s_other_value)
        if isdegenerated(s_new_value) and self.bookkeeper:
            self.bookkeeper.ondegenerated(self, s_new_value)        
        updated = s_new_value != self.s_value
        if updated:
            self.s_value = s_new_value
            # reflow from all reading points
            for position_key in self.read_locations:
                self.bookkeeper.annotator.reflowfromposition(position_key)
        return updated


class ListDef:
    """A list definition remembers how general the items in that particular
    list have to be.  Every list creation makes a new ListDef, and the union
    of two lists merges the ListItems that each ListDef stores."""

    def __init__(self, bookkeeper, s_item=SomeImpossibleValue()):
        self.listitem = ListItem(bookkeeper, s_item)
        self.listitem.itemof[self] = True
        self.bookkeeper = bookkeeper

    def getbookkeeper(self):
        if self.bookkeeper is None:
            from pypy.annotation.bookkeeper import getbookkeeper
            return getbookkeeper()
        else:
            return self.bookkeeper

    def read_item(self, position_key=None):
        if position_key is None:
            position_key = self.getbookkeeper().position_key
        self.listitem.read_locations[position_key] = True
        return self.listitem.s_value

    def same_as(self, other):
        return self.listitem is other.listitem

    def union(self, other):
        if (self.same_as(MOST_GENERAL_LISTDEF) or
            other.same_as(MOST_GENERAL_LISTDEF)):
            return MOST_GENERAL_LISTDEF   # without merging
        else:
            self.listitem.merge(other.listitem)
            return self

    def agree(self, other):
        s_self_value = self.read_item()
        s_other_value = other.read_item()
        self.generalize(s_other_value)
        other.generalize(s_self_value)

    def offspring(self, *others):
        s_self_value = self.read_item()
        s_other_values = []
        for other in others:
            s_other_values.append(other.read_item())
        s_newlst = self.getbookkeeper().newlist(s_self_value, *s_other_values)
        s_newvalue = s_newlst.listdef.read_item()
        self.generalize(s_newvalue)
        for other in others:
            other.generalize(s_newvalue)
        return s_newlst

    def generalize(self, s_value):
        self.listitem.generalize(s_value)

    def __repr__(self):
        return '<[%r]>' % (self.listitem.s_value,)

    def mutate(self):
        self.listitem.mutated = True

    def resize(self):
        self.listitem.mutated = True
        self.listitem.resized = True


MOST_GENERAL_LISTDEF = ListDef(None, SomeObject())
