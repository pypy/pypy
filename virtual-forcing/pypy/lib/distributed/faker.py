
""" This file is responsible for faking types
"""

class GetSetDescriptor(object):
    def __init__(self, protocol, name):
        self.protocol = protocol
        self.name = name

    def __get__(self, obj, type=None):
        return self.protocol.get(self.name, obj, type)

    def __set__(self, obj, value):
        self.protocol.set(self.name, obj, value)

class GetDescriptor(object):
    def __init__(self, protocol, name):
        self.protocol = protocol
        self.name = name

    def __get__(self, obj, type=None):
        return self.protocol.get(self.name, obj, type)

# these are one-go functions for wrapping/unwrapping types,
# note that actual caching is defined in other files,
# this is only the case when we *need* to wrap/unwrap
# type

from types import MethodType, FunctionType

def not_ignore(name):
    # we don't want to fake some default descriptors, because
    # they'll alter the way we set attributes
    l = ['__dict__', '__weakref__', '__class__', '__bases__',
         '__getattribute__', '__getattr__', '__setattr__',
         '__delattr__']
    return not name in dict.fromkeys(l)

def wrap_type(protocol, tp, tp_id):
    """ Wrap type to transpotable entity, taking
    care about descriptors
    """
    dict_w = {}
    for item in tp.__dict__.keys():
        value = getattr(tp, item)
        if not_ignore(item):
            # we've got shortcut for method
            if hasattr(value, '__get__') and not type(value) is MethodType:
                if hasattr(value, '__set__'):
                    dict_w[item] = ('get', item)
                else:
                    dict_w[item] = ('set', item)
            else:
                dict_w[item] = protocol.wrap(value)
    bases_w = [protocol.wrap(i) for i in tp.__bases__ if i is not object]
    return tp_id, tp.__name__, dict_w, bases_w

def unwrap_descriptor_gen(desc_class):
    def unwrapper(protocol, data):
        name = data
        obj = desc_class(protocol, name)
        obj.__name__ = name
        return obj
    return unwrapper

unwrap_get_descriptor = unwrap_descriptor_gen(GetDescriptor)
unwrap_getset_descriptor = unwrap_descriptor_gen(GetSetDescriptor)

def unwrap_type(objkeeper, protocol, type_id, name_, dict_w, bases_w):
    """ Unwrap remote type, based on it's description
    """
    if bases_w == []:
        bases = (object,)
    else:
        bases = tuple([protocol.unwrap(i) for i in bases_w])
    d = dict.fromkeys(dict_w)
    # XXX we do it in two steps to avoid cyclic dependencies,
    #     probably there is some smarter way of doing this
    if '__doc__' in dict_w:
        d['__doc__'] = protocol.unwrap(dict_w['__doc__'])
    tp = type(name_, bases, d)
    objkeeper.register_remote_type(tp, type_id)
    for key, value in dict_w.items():
        if key != '__doc__':
            v = protocol.unwrap(value)
            if isinstance(v, FunctionType):
                setattr(tp, key, staticmethod(v))
            else:
                setattr(tp, key, v)
