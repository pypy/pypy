# a global (per-space) version counter to track live instances which "compare
# by identity" (i.e., whose __eq__, __cmp__ and __hash__ are the default
# ones).  The idea is to track only classes for which we checked the
# compares_by_identity() status at least once: we increment the version if its
# status might change, e.g. because we set one of those attributes.  The
# actual work is done by W_TypeObject.mutated() and objecttype:descr_setclass

def bump_global_version(space):
    if space.config.objspace.std.withidentitydict:
        space.fromcache(ComparesByIdentityVersion).bump()

def get_global_version(space):
    if space.config.objspace.std.withidentitydict:
        return space.fromcache(ComparesByIdentityVersion).get()
    return None

class ComparesByIdentityVersion(object):

    def __init__(self, space):
        self.bump()

    def bump(self):
        from pypy.objspace.std.typeobject import VersionTag
        self._version = VersionTag()

    def get(self):
        return self._version
