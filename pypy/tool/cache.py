
# hacks += 1
class Cache:
    frozen = True 

    def __init__(self):
        self.content = {}
        self.frozen = False

    def __hash__(self):
        if not self.frozen: 
            #raise TypeError, "cannot get hash of un-frozen cache"
            self.freeze()
        return id(self)

    def clear(self):
        if self.frozen:
            raise TypeError, "cannot clear frozen cache"
        self.content.clear()

    def getorbuild(self, key, builder, stuff):
        try:
            return self.content[key]
        except KeyError:
            assert not self.frozen, "cannot build %r, cache already frozen" % key
            result = builder(key, stuff)
            #assert key not in self.content, "things messed up"
            self.content[key] = result
            return result
    # note to annotator: we want loadfromcache() to be 
    # specialized for the different cache types 
    getorbuild._specialize_ = "location"

    def freeze(self):
        try:
            del self.frozen
        except AttributeError:
            pass
        return True

    _freeze_ = freeze
