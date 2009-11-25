from pypy.rlib.objectmodel import r_dict
from pypy.rpython.microbench.microbench import MetaBench

class Obj:
    def __init__(self, x):
        self.x = x

def myhash(obj):
    return obj.x

def mycmp(obj1, obj2):
    return obj1.x == obj2.x

class Space:
    def myhash(self, obj):
        return obj.x

    def mycmp(self, obj1, obj2):
        return obj1.x == obj2.x

    def _freeze_(self):
        return True

space = Space()
obj1 = Obj(1)
obj2 = Obj(2)

class r_dict__set_item:
    __metaclass__ = MetaBench

    def init():
        return r_dict(mycmp, myhash)
    args = ['obj', 'i']
    def loop(obj, i):
        obj[obj1] = i
        obj[obj2] = i

class r_dict__get_item:
    __metaclass__ = MetaBench

    def init():
        res = r_dict(mycmp, myhash)
        res[obj1] = 42
        res[obj2] = 43
        return res
    args = ['obj', 'i']
    def loop(obj, i):
        return obj[obj1] + obj[obj2]

class r_dict__frozen_pbc__set_item:
    __metaclass__ = MetaBench

    def init():
        return r_dict(space.mycmp, space.myhash)
    args = ['obj', 'i']
    def loop(obj, i):
        obj[obj1] = i
        obj[obj2] = i

class r_dict__frozen_pbc__get_item:
    __metaclass__ = MetaBench

    def init():
        res = r_dict(space.mycmp, space.myhash)
        res[obj1] = 42
        res[obj2] = 43
        return res
    args = ['obj', 'i']
    def loop(obj, i):
        return obj[obj1] + obj[obj2]
