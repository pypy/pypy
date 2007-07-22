
from pypy.rpython.ootypesystem.bltregistry import BasicExternal, described

#class Jvm(object):
#    def __getattr__(self, name):
#        return None

class Jvm(object):
    pass

class Random(BasicExternal):
    @described(retval=int)
    def nextInt(self):
        pass

Jvm.Random = Random
