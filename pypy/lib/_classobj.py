import sys

obj_setattr = object.__setattr__
obj_getattribute = object.__getattribute__

MASK = sys.maxint * 2 + 2

def uid(o):
    return (MASK + id(o)) & (MASK-1)

def type_err(arg, expected, v):
   raise TypeError("argument %s must be %s, not %s" % (arg, expected, type(v).__name__))

def set_name(cls, name):
    if not isinstance(name, str):
        raise TypeError, "__name__ must be a string object"
    obj_setattr(cls, '__name__', name)

def set_bases(cls, bases):
    if not isinstance(bases, tuple):
        raise TypeError, "__bases__ must be a tuple object"
    for b in bases:
        if not isinstance(b, classobj):
            raise TypeError, "__bases__ items must be classes"
    obj_setattr(cls, '__bases__', bases)

def set_dict(cls, dic):
    if not isinstance(dic, dict):
        raise TypeError, "__dict__ must be a dictionary object"
    # preserved __name__ and __bases__
    dic['__name__'] = cls.__name__
    dic['__bases__'] = cls.__bases__
    obj_setattr(cls, '__dict__', dic)

def retrieve(cls, attr):
    dic = obj_getattribute(cls, '__dict__')
    try:
        return dic[attr]
    except KeyError:
        raise AttributeError, attr

def lookup(cls, attr):
    # returns (value, class it was found in)
    try:
        v = retrieve(cls, attr)
        return v, cls
    except AttributeError:
        for b in obj_getattribute(cls, '__bases__'):
            v, found = lookup(b, attr)
            if found:
                return v, found
        return None, None

def mro_lookup(v, name):
    try:
        mro = type(v).__mro__
    except AttributeError:
        return None
    for x in mro:
        if name in x.__dict__:
            return x.__dict__[name]
    return None
    

class classobj(object):

    def __new__(subtype, name, bases, dic):
        if not isinstance(name, str):
            type_err('name', 'string', name)

        if bases is None:
            bases = ()

        if not isinstance(bases, tuple):
            type_err('bases', 'tuple', bases)
        
        if not isinstance(dic, dict):
            type_err('dict', 'dict', dic)

        try:
            dic['__doc__']
        except KeyError:
            dic['__doc__'] = None

        try:
            dic['__module__']
        except KeyError:
            try:
                g = sys._getframe(1).f_globals
            except ValueError:
                pass
            else:
                modname = g.get('__name__', None)
                if modname is not None:
                    dic['__module__'] = modname
            
        for b in bases:
            if not isinstance(b, classobj):
                if callable(type(b)):
                    return type(b)(name, bases, dic)
                raise TypeError,"base must be class"

        
        new_class = object.__new__(classobj)

        obj_setattr(new_class, '__dict__', dic)
        obj_setattr(new_class, '__name__', name)
        obj_setattr(new_class, '__bases__', bases)

        return new_class

    def __setattr__(self, attr, value):
        if attr == '__name__':
            set_name(self, value)
        elif attr == '__bases__':
            set_bases(self, value)
        elif attr == '__dict__':
            set_dict(self, value)
        else:
            obj_setattr(self, attr, value)
    
    def __delattr__(self, attr):
        if attr in ('__name__', '__bases__', '__dict__'):
            classobj.__setattr__(self, attr, None)
        else:
            object.__delattr__(self, attr)
    

    def __getattribute__(self, attr):
        if attr == '__dict__':
            return obj_getattribute(self, '__dict__')
        v, found = lookup(self, attr)
        if not found:
            raise AttributeError, "class %s has no attribute %s" % (self.__name__, attr)
        if attr in ('__name__', '__bases__'):
            return v

        descr_get = mro_lookup(v, '__get__')
        if descr_get is None:
            return v
        return descr_get(v, None, self)
        
    def __repr__(self):
        try:
            mod = retrieve(self, '__module__')
            if not isinstance(mod, str):
                mod = None
        except AttributeError:
            mod = None
        if mod is None:
            return "<class ?.%s at 0x%x>" % (self.__name__, uid(self))
        else:
            return "<class %s.%s at 0x%x>" % (mod, self.__name__, uid(self))

    def __str__(self):
        try:
            mod = retrieve(self, '__module__')
            if not isinstance(mod, str):
                mod = None
        except AttributeError:
            mod = None
        if mod is None:
            return self.__name__
        else:
            return "%s.%s" % (mod, self.__name__)


class instance(object):
    pass
 
            
