
# hacks += 1
class frozendict(dict):
    def __setitem__(self, *args): 
        raise TypeError, "this dict is already frozen, you are too late!" 
    __delitem__ = setdefault = update = pop = popitem = clear = __setitem__ 

    def __hash__(self):
        return id(self) 

