from pypy.rpython.microbench.microbench import MetaBench

class str_dict__set_item:
    __metaclass__ = MetaBench

    def init():
        return {}
    args = ['obj', 'i']
    def loop(obj, i):
        obj['foo'] = i
        obj['bar'] = i

class str_dict__get_item:
    __metaclass__ = MetaBench

    def init():
        return {'foo': 0, 'bar': 1}
    args = ['obj', 'i']
    def loop(obj, i):
        return obj['foo'] + obj['bar']

class int_dict__set_item:
    __metaclass__ = MetaBench

    def init():
        return {}
    args = ['obj', 'i']
    def loop(obj, i):
        obj[42] = i
        obj[43] = i

class int_dict__get_item:
    __metaclass__ = MetaBench

    def init():
        return {42: 0, 43: 1}
    args = ['obj', 'i']
    def loop(obj, i):
        return obj[42] + obj[43]


class Foo:
    pass

obj1 = Foo()
obj2 = Foo()

class obj_dict__set_item:
    __metaclass__ = MetaBench

    def init():
        return {}
    args = ['obj', 'i']
    def loop(obj, i):
        obj[obj1] = i
        obj[obj2] = i

class obj_dict__get_item:
    __metaclass__ = MetaBench

    def init():
        return {obj1: 0, obj2: 1}
    args = ['obj', 'i']
    def loop(obj, i):
        return obj[obj1] + obj[obj2]
