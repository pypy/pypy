from pypy.rpython.microbench.microbench import MetaBench

class ListAppend:
    __metaclass__ = MetaBench
    def init():
        return []
    args = ['obj', 'i']
    def loop(obj, i):
        obj.append(i)
    
class ListGetItem:
    __metaclass__ = MetaBench
    LOOPS = 100000000
    def init():
        obj = []
        for i in xrange(1000):
            obj.append(i)
        return obj
    args = ['obj', 'i']
    def loop(obj, i):
        return obj[i%1000]

class ListSetItem:
    __metaclass__ = MetaBench
    LOOPS = 100000000
    def init():
        obj = []
        for i in xrange(1000):
            obj.append(i)
        return obj
    args = ['obj', 'i']
    def loop(obj, i):
        obj[i%1000] = i

class FixedListGetItem:
    __metaclass__ = MetaBench
    LOOPS = 100000000
    def init():
        return [0] * 1000
    args = ['obj', 'i']
    def loop(obj, i):
        return obj[i%1000]

class FixedListSetItem:
    __metaclass__ = MetaBench
    LOOPS = 100000000
    def init():
        return [0] * 1000
    args = ['obj', 'i']
    def loop(obj, i):
        obj[i%1000] = i
