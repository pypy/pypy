from pypy.annotation.model import SomeObject, s_ImpossibleValue
from pypy.annotation.model import SomeList, SomeString
from pypy.annotation.model import unionof, TLS, UnionError, isdegenerated


class TooLateForChange(Exception):
    pass

class ListItem:
    mutated = False    # True for lists mutated after creation
    resized = False    # True for lists resized after creation
    range_step = None  # the step -- only for lists only created by a range()
    dont_change_any_more = False   # set to True when too late for changes

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
        self.dont_resize = False
        if bookkeeper is None:
            self.dont_change_any_more = True

    def mutate(self):
        if not self.mutated:
            if self.dont_change_any_more:
                raise TooLateForChange
            self.mutated = True

    def resize(self):
        if not self.resized:
            if self.dont_change_any_more or self.dont_resize:
                raise TooLateForChange
            self.resized = True

    def setrangestep(self, step):
        if step != self.range_step:
            if self.dont_change_any_more:
                raise TooLateForChange
            self.range_step = step

    def merge(self, other):
        if self is not other:
            if getattr(TLS, 'no_side_effects_in_union', 0):
                raise UnionError("merging list/dict items")

            if other.dont_change_any_more:
                if self.dont_change_any_more:
                    raise TooLateForChange
                else:
                    # lists using 'other' don't expect it to change any more,
                    # so we try merging into 'other', which will give
                    # TooLateForChange if it actually tries to make
                    # things more general
                    self, other = other, self

            if other.dont_resize:
                if self.resized:                    
                    raise TooLateForChange()
                self.dont_resize = True
            if other.mutated: self.mutate()
            if other.resized:
                self.resize()
            if other.range_step != self.range_step:
                self.setrangestep(self._step_map[type(self.range_step),
                                                 type(other.range_step)])
            self.itemof.update(other.itemof)
            read_locations = self.read_locations.copy()
            other_read_locations = other.read_locations.copy()
            self.read_locations.update(other.read_locations)
            self.patch()    # which should patch all refs to 'other'
            s_value = self.s_value
            s_other_value = other.s_value
            s_new_value = unionof(s_value, s_other_value)
            if isdegenerated(s_new_value):
                if self.bookkeeper:
                    self.bookkeeper.ondegenerated(self, s_new_value)
                elif other.bookkeeper:
                    other.bookkeeper.ondegenerated(other, s_new_value)
            if s_new_value != s_value:
                if self.dont_change_any_more:
                    raise TooLateForChange
                self.s_value = s_new_value
                # reflow from reading points
                for position_key in read_locations:
                    self.bookkeeper.annotator.reflowfromposition(position_key) 
            if s_new_value != s_other_value:
                # reflow from reading points
                for position_key in other_read_locations:
                    other.bookkeeper.annotator.reflowfromposition(position_key)

    def patch(self):
        for listdef in self.itemof:
            listdef.listitem = self

    def generalize(self, s_other_value):
        s_new_value = unionof(self.s_value, s_other_value)
        if isdegenerated(s_new_value) and self.bookkeeper:
            self.bookkeeper.ondegenerated(self, s_new_value)        
        updated = s_new_value != self.s_value
        if updated:
            if self.dont_change_any_more:
                raise TooLateForChange
            self.s_value = s_new_value
            # reflow from all reading points
            for position_key in self.read_locations:
                self.bookkeeper.annotator.reflowfromposition(position_key)
        return updated


class ListDef:
    """A list definition remembers how general the items in that particular
    list have to be.  Every list creation makes a new ListDef, and the union
    of two lists merges the ListItems that each ListDef stores."""

    def __init__(self, bookkeeper, s_item=s_ImpossibleValue,
                 mutated=False, resized=False):
        self.listitem = ListItem(bookkeeper, s_item)
        self.listitem.mutated = mutated | resized
        self.listitem.resized = resized
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
        return '<[%r]%s%s>' % (self.listitem.s_value,
                               self.listitem.mutated and 'm' or '',
                               self.listitem.resized and 'r' or '')

    def mutate(self):
        self.listitem.mutate()

    def resize(self):
        self.listitem.mutate()
        self.listitem.resize()

    def never_resize(self):
        if self.listitem.resized:
            raise TooLateForChange()
        self.listitem.dont_resize = True


MOST_GENERAL_LISTDEF = ListDef(None, SomeObject())

s_list_of_strings = SomeList(ListDef(None, SomeString(), resized = True))
