import sys, operator

def coerce(left, right):
    # XXX this is just a surrogate for now
    # XXX the builtin coerce needs to be implemented by PyPy
    return None

obj_setattr = object.__setattr__
obj_getattribute = object.__getattribute__

MASK = sys.maxint * 2 + 1

def uid(o):
    v = id(o)
    if v < 0:
        v += MASK
        v += 1
    return v & MASK

def type_err(arg, expected, v):
   return TypeError("argument %s must be %s, not %s" % (arg, expected, type(v).__name__))

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

def retrieve(obj, attr):
    dic = obj_getattribute(obj, '__dict__')
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

def get_class_module(cls):
    try:
        mod = retrieve(cls, "__module__")
    except AttributeError:
        mod = None
    if not isinstance(mod, str):
        return "?"
    return mod

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
            raise type_err('name', 'string', name)

        if bases is None:
            bases = ()

        if not isinstance(bases, tuple):
            raise type_err('bases', 'tuple', bases)
        
        if not isinstance(dic, dict):
            raise type_err('dict', 'dict', dic)

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
        mod = get_class_module(self)
        return "<class %s.%s at 0x%x>" % (mod, self.__name__, uid(self))

    def __str__(self):
        mod = get_class_module(self)
        if mod == "?":
            return self.__name__
        else:
            return "%s.%s" % (mod, self.__name__)

    def __call__(self, *args, **kwds):
        inst = object.__new__(instance)
        dic = inst.__dict__
        dic['__class__'] = self
        init = instance_getattr1(inst,'__init__', False)
        if init:
            ret = init(*args, **kwds)
            if ret is not None:
                raise TypeError("__init__() should return None")
        return inst

# first we use the object's dict for the instance dict.
# with a little more effort, it should be possible
# to provide a clean extra dict with no other attributes
# in it.

def instance_getattr1(inst, name, exc=True):
    if name == "__dict__":
        return obj_getattribute(inst, name)
    elif name == "__class__":
        # for now, it lives in the instance dict
        return retrieve(inst, name)
    try:
        return retrieve(inst, name)
    except AttributeError:
        cls = retrieve(inst, "__class__")
        v, found = lookup(cls, name)
        if not found:
            if exc:
                raise AttributeError, "%s instance has no attribute %s" % (cls.__name__, name)
            else:
                return None
        descr_get = mro_lookup(v, '__get__')
        if descr_get is None:
            return v
        return descr_get(v, inst, cls)

class instance(object):
    def __getattribute__(self, name):
        try:
            return instance_getattr1(self, name)
        except AttributeError:
            getattr = instance_getattr1(self, '__getattr__', exc=False)
            if getattr is not None:
                return getattr(name)
            raise
            
    def __new__(typ, klass, dic=None):
        # typ is not used at all
        if not isinstance(klass,classobj):
            raise TypeError("instance() first arg must be class")
        if dic is None:
            dic = {}
        elif not isinstance(dic, dict):
            raise TypeError("instance() second arg must be dictionary or None")
        inst = object.__new__(instance)
        dic['__class__'] = klass
        obj_setattr(inst, '__dict__', dic)
        return inst

    def __setattr__(self, name, value):
        if name == '__dict__':
            if not isinstance(value, dict):
                raise TypeError("__dict__ must be set to a dictionary")
            # for now, we need to copy things, because we are using
            # the __dict__for our class as well. This will vanish!
            value['__class__'] = self.__class__
            obj_setattr(inst, '__dict__', value)
        elif name == '__class__':
            if not isinstance(value, classobj):
                raise TypeError("__class__ must be set to a class")
            self.__dict__['__class__'] = value
        else:
            setattr = instance_getattr1(self, '__setattr__', exc=False)
            if setattr is not None:
                setattr(name, value)
            else:
                self.__dict__[name] = value

    def __delattr__(self, name):
        # abuse __setattr__ to get the complaints :-)
        # this is as funny as in CPython
        if name in ('__dict__', '__class__'):
            instance.__setattr__(self, name, None)
        else:
            delattr = instance_getattr1(self, '__delattr__', exc=False)
            if delattr is not None:
                delattr(name)
            else:
                try:
                    del self.__dict__[name]
                except KeyError, ex:
                    raise AttributeError("%s instance has no attribute '%s'" % (
                        self.__class__.__name__,name) )

    def __repr__(self):
        try:
            func = instance_getattr1(self, '__repr__')
        except AttributeError:
            klass = self.__class__
            mod = get_class_module(klass)
            return "<%s.%s instance at 0x%x>" % (mod, klass.__name__, uid(self))
        return func()

    def __str__(self):
        try:
            func = instance_getattr1(self, '__str__')
        except AttributeError:
            return instance.__repr__(self)
        return func()

    def __hash__(self):
        _eq = instance_getattr1(self, "__eq__", False)
        _cmp = instance_getattr1(self, "__cmp__", False)
        _hash = instance_getattr1(self, "__hash__", False)
        if (_eq or _cmp) and not _hash:
            raise TypeError("unhashable instance")
        if _hash:
            ret = _hash()
            if not isinstance(ret, int):
                raise TypeError("__hash__() should return an int")
            return ret
        else:
            return id(self)

    def __len__(self):
        ret = instance_getattr1(self,'__len__')()
        if isinstance(ret, int):
            if ret < 0:
                raise ValueError("__len__() should return >= 0")
            return ret
        else:
            raise TypeError("__len__() should return an int")

    def __getitem__(self, key):
        if isinstance(key, slice) and key.step is None:
            func = instance_getattr1(self, '__getslice__', False)
            if func:
                return func(key.start, key.stop)
        return instance_getattr1(self, '__getitem__')(key)

    def __setitem__(self, key, value):
        if isinstance(key, slice) and key.step is None:
            func = instance_getattr1(self, '__setslice__', False)
            if func:
                func(key.start, key.stop, value)
        instance_getattr1(self, '__setitem__')(key, value)

    def __delitem__(self, key):
        if isinstance(key, slice) and key.step is None:
            func = instance_getattr1(self, '__delslice__', False)
            if func:
                func(key.start, key.stop)
        instance_getattr1(self, '__delitem__')(key)

    def __contains__(self, obj):
        func = instance_getattr1(self, '__contains__', False)
        if func:
            return bool(func(obj))
        # now do it ourselves
        for x in self:
            if x == obj:
                return True
        return False

    # unary operators
    for op in "neg pos abs invert int long float oct hex".split():
        exec ("""
def __%(op)s__(self):
   return instance_getattr1(self, '__%(op)s__')()
""") % {"op": op}
    del op


    # binary operators    
    for op in "or and xor lshift rshift add sub mul div mod divmod floordiv truediv".split():
        exec("""
def __%(op)s__(self, other):
    coerced = coerce(self, other)
    if coerced is None or coerced[0] is self:
        func = instance_getattr1(self, '__%(op)s__', False)
        if func:
            return func(other)
        return NotImplemented
    else:
        return operator.%(op2)s(self, other)

def __r%(op)s__(self, other):
    coerced = coerce(self, other)
    if coerced is None or coerced[0] is self:
        func = instance_getattr1(self, '__r%(op)s__', False)
        if func:
            return func(other)
        return NotImplemented
    else:
        return operator.%(op2)s(other, self)
""") % {"op": op, "op2": (op, op+'_')[op in ('and', 'or', 'not')]}
    del op


    # inplace operators    
    for op in 'mod and pow truediv lshift xor rshift floordiv div sub mul add or'.split():
        exec ("""
def __i%(op)s__(self, other):
   func = instance_getattr1(self, '__i%(op)s__', False)
   if func:
       return func(other)
   return NotImplemented

""") % {"op": op}
    del op


    def __pow__(self, other, modulo=None):
        if modulo is None:
            coerced = coerce(self, other)
            if coerced is None or coerced[0] is self:
                func = instance_getattr1(self, '__pow__', False)
                if func:
                    return func(other)
                return NotImplemented
            else:
                return operator.pow(self, other)
        else:
            # CPython also doesn't try coercion in this case
            func = instance_getattr1(self, '__pow__', False)
            if func:
                return func(other, modulo)
            return NotImplemented


    def __rpow__(self, other, modulo=None):
        if modulo is None:
            coerced = coerce(self, other)
            if coerced is None or coerced[0] is self:
                func = instance_getattr1(self, '__rpow__', False)
                if func:
                    return func(other)
                return NotImplemented
            else:
                return operator.pow(other, self)
        else:
            # CPython also doesn't try coercion in this case
            func = instance_getattr1(self, '__rpow__', False)
            if func:
                return func(other, modulo)
            return NotImplemented


    def __nonzero__(self):
        func = instance_getattr1(self, '__nonzero__', False)
        if not func:
            func = instance_getattr1(self, '__nonzero__', False)
            if not func: # default to true
                return True
        ret = func()
        if isinstance(ret, int):
            if ret < 0:
                raise ValueError("__nonzero__() should return >= 0")
            return ret > 0
        else:
            raise TypeError("__nonzero__() should return an int")        


    def __call__(self, *args, **kwds):
        func = instance_getattr1(self, '__call__', False)
        if not func:
            raise AttributeError, "%s instance has no __call__ method" % (self.__class__.__name__)            
        return func(*args, **kwds)

    # rich comparison operations
    for op in 'eq ne gt lt ge le'.split():
        exec ("""
def __%(op)s__(self, other):
        try:
            return instance_getattr1(self, '__%(op)s__')(other)
        except AttributeError:
            return NotImplemented

""") % {"op": op}
    del op    


    def __iter__(self):
        func = instance_getattr1(self, '__iter__', False)
        if func:
            ret = func()
            if not mro_lookup(ret, 'next'):
                raise TypeError, ("__iter__ returned non-iterator of type %s"
                                  % type(ret).__name__)
            return ret
        func = instance_getattr1(self, '__getitem__')
        if not func:
            raise TypeError, "iteration over non-sequence"
        def seqiter(): # XXX may want to access and instatiate the internal
                       # sequence-iterator type instead
            i = 0
            while 1:
                try:
                    yield func(i)
                except IndexError:
                    return
                i += 1
        return seqiter()

    def next(self):
        func = instance_getattr1(self, '__next__', False)
        if not func:
            raise TypeError, "instance has no next() method"
        return func()

    def __cmp__(self, other): # do all the work here like CPython
        coerced = coerce(self, other)
        if coerced is None:
            v = self
            w = other
        else:
            v = coerced[0]
            w = coerced[1]
            if not isinstance(v, instance) and not isinstance(w, instance):
                return operator.cmp(v,w)
        if isinstance(v, instance):
            func = instance_getattr1(v, '__cmp__', False)
            if func:
                res = func(w)
                if isinstance(res, int):
                    if res > 0:
                        return 1
                    if res < 0:
                        return -1
                    return 0
                raise TypeError,"__cmp__ must return int"
        if isinstance(w, instance):
            func = instance_getattr1(v, '__cmp__', False)
            if func:
                res = func(v)
                if isinstance(res, int):
                    if res > 0:
                        return 1
                    if res < 0:
                        return -1
                    return 0
                raise TypeError,"__cmp__ must return int"
        return NotImplemented
    
