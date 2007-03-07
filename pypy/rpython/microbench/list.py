from pypy.rpython.microbench.microbench import MetaBench

class list__append:
    __metaclass__ = MetaBench
    def init():
        return []
    args = ['obj', 'i']
    def loop(obj, i):
        obj.append(i)
    
class list__get_item:
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

class list__set_item:
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

class fixed_list__get_item:
    __metaclass__ = MetaBench
    LOOPS = 100000000
    def init():
        return [0] * 1000
    args = ['obj', 'i']
    def loop(obj, i):
        return obj[i%1000]

class fixed_list__set_item:
    __metaclass__ = MetaBench
    LOOPS = 100000000
    def init():
        return [0] * 1000
    args = ['obj', 'i']
    def loop(obj, i):
        obj[i%1000] = i

class list__iteration__int:
    __metaclass__ = MetaBench
    LOOPS = 100000
    def init():
        obj = [0]*1000
        obj[0] = 42
        return obj
    args = ['obj']
    def loop(obj):
        tot = 0
        for item in obj:
            tot += item
        return tot

class list__iteration__string:
    __metaclass__ = MetaBench
    LOOPS = 100000
    def init():
        obj = ['foo']*1000
        obj[0] = 'bar'
        return obj
    args = ['obj']
    def loop(obj):
        tot = 0
        for item in obj:
            tot += len(item)
        return tot
