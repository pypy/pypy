
class basecache(dict): 
    pass

# hacks += 1
class Cache(dict):
    frozen = True 

    def __init__(self, *args):  
        self.frozen = False
        dict.__init__(self, *args) 

    for x in ('__setitem__', '__delitem__', 'setdefault', 'update',
              'pop', 'popitem', 'clear'):
        l=["def %s(self, *args):",
           "   assert not self.frozen, 'cache already frozen'",
           "   return dict.%s(self, *args)"]
        exec "\n".join(l) % (x,x)
         
    def __hash__(self):
        if not self.frozen: 
            raise TypeError, "cannot get hash of un-frozen cache"
        return id(self) 

    def getorbuild(self, key, builder, space):
        try:
            return self[key]
        except KeyError:
            assert not self.frozen, "cannot build %r, cache already frozen" % key
            return self.setdefault(key, builder(key, space))
    # note to annotator: we want loadfromcache() to be 
    # specialized for the different cache types 
    getorbuild._specialize_ = "location"

    def freeze(self):
        del self.frozen 
