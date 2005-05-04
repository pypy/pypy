"""
Caches that can freeze when the annotator needs it.
"""

#
# _freeze_() protocol:
#     user-defined classes can define a method _freeze_(), which
#     is called when a prebuilt instance is found.  If the method
#     returns True, the instance is considered immutable and becomes
#     a SomePBC().  Otherwise it's just SomeInstance().  The method
#     should force away any laziness that remains in the instance.
#
# Cache class:
#     a cache meant to map a finite number of keys to values.
#     It is normally extended lazily, until it contains all possible
#     keys.  The _specialize_ attribute of the getorbuild() method
#     forces the annotator to decode the argument's annotations,
#     which must be constants or SomePBCs, actually call the
#     method with all possible combinations, and gather the results.
#     The idea is to completely fill the cache at annotation-time,
#     using the information collected by the annotator itself about
#     what the keys can actually be.
#


class Cache:
    def __init__(self):
        self.content = {}

    def getorbuild(self, key, builder, stuff):
        try:
            return self.content[key]
        except KeyError:
            result = builder(key, stuff)
            #assert key not in self.content, "things messed up"
            self.content[key] = result
            return result
    getorbuild._specialize_ = "memo"

    def _freeze_(self):
        # needs to be SomePBC, but otherwise we can't really freeze the
        # cache because more getorbuild() calls might be discovered later
        # during annotation.
        return True
