
# hacks += 1
class frozendict(dict):
    _hash_cache = None
    def __setitem__(self, *args):
        raise TypeError, "this dict is already frozen, you are too late!" 
    __delitem__ = setdefault = update = pop = popitem = clear = __setitem__

    def __hash__(self):
        rval = self._hash_cache
        if rval is None:
            dct = self.items()
            dct.sort()
            rval = self._hash_cache = hash(tuple(dct)) ^ 0x18293742
        return rval

