""" A very simple cell dict implementation. The dictionary maps keys to cell.
This ensures that the function (dict, key) -> cell is pure. By itself, this
optimization is not helping at all, but in conjunction with the JIT it can
speed up global lookups a lot."""

from pypy.objspace.std.dictmultiobject import IteratorImplementation
from pypy.objspace.std.dictmultiobject import W_DictMultiObject, _is_sane_hash
from pypy.rlib import jit

class ModuleCell(object):
    def __init__(self, w_value=None):
        self.w_value = w_value

    def invalidate(self):
        w_value = self.w_value
        self.w_value = None
        return w_value

    def __repr__(self):
        return "<ModuleCell: %s>" % (self.w_value, )

class ModuleDictImplementation(W_DictMultiObject):
    def __init__(self, space):
        self.space = space
        self.content = {}

    def getcell(self, key, makenew):
        if makenew or jit.we_are_jitted():
            # when we are jitting, we always go through the pure function
            # below, to ensure that we have no residual dict lookup
            self = jit.hint(self, promote=True)
            return self._getcell_makenew(key)
        return self.content.get(key, None)

    @jit.purefunction
    def _getcell_makenew(self, key):
        res = self.content.get(key, None)
        if res is not None:
            return res
        result = self.content[key] = ModuleCell()
        return result

    def impl_setitem(self, w_key, w_value):
        space = self.space
        if space.is_w(space.type(w_key), space.w_str):
            self.impl_setitem_str(self.space.str_w(w_key), w_value)
        else:
            self._as_rdict().setitem(w_key, w_value)

    def impl_setitem_str(self, name, w_value, shadows_type=True):
        self.getcell(name, True).w_value = w_value

    def impl_delitem(self, w_key):
        space = self.space
        w_key_type = space.type(w_key)
        if space.is_w(w_key_type, space.w_str):
            key = space.str_w(w_key)
            cell = self.getcell(key, False)
            if cell is None or cell.w_value is None:
                raise KeyError
            # note that we don't remove the cell from self.content, to make
            # sure that a key that was found at any point in the dict, still
            # maps to the same cell later (even if this cell no longer
            # represents a key)
            cell.invalidate()
        elif _is_sane_hash(space, w_key_type):
            raise KeyError
        else:
            self._as_rdict().delitem(w_key)
        
    def impl_length(self):
        # inefficient, but do we care?
        res = 0
        for cell in self.content.itervalues():
            if cell.w_value is not None:
                res += 1
        return res

    def impl_getitem(self, w_lookup):
        space = self.space
        w_lookup_type = space.type(w_lookup)
        if space.is_w(w_lookup_type, space.w_str):
            return self.impl_getitem_str(space.str_w(w_lookup))

        elif _is_sane_hash(space, w_lookup_type):
            return None
        else:
            return self._as_rdict().getitem(w_lookup)

    def impl_getitem_str(self, lookup):
        res = self.getcell(lookup, False)
        if res is None:
            return None
        # note that even if the res.w_value is None, the next line is fine
        return res.w_value

    def impl_iter(self):
        return ModuleDictIteratorImplementation(self.space, self)

    def impl_keys(self):
        space = self.space
        return [space.wrap(key) for key, cell in self.content.iteritems()
                    if cell.w_value is not None]

    def impl_values(self):
        return [cell.w_value for cell in self.content.itervalues()
                    if cell.w_value is not None]

    def impl_items(self):
        space = self.space
        return [space.newtuple([space.wrap(key), cell.w_value])
                    for (key, cell) in self.content.iteritems()
                        if cell.w_value is not None]

    def impl_clear(self):
        for k, cell in self.content.iteritems():
            cell.invalidate()

    def _as_rdict(self):
        r_dict_content = self.initialize_as_rdict()
        for k, cell in self.content.iteritems():
            if cell.w_value is not None:
                r_dict_content[self.space.wrap(k)] = cell.w_value
            cell.invalidate()
        self._clear_fields()
        return self

    def _clear_fields(self):
        self.content = None

class ModuleDictIteratorImplementation(IteratorImplementation):
    def __init__(self, space, dictimplementation):
        IteratorImplementation.__init__(self, space, dictimplementation)
        self.iterator = dictimplementation.content.iteritems()

    def next_entry(self):
        for key, cell in self.iterator:
            if cell.w_value is not None:
                return (self.space.wrap(key), cell.w_value)
        else:
            return None, None
