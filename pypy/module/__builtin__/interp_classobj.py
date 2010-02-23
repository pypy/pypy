import new
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.gateway import ObjSpace, W_Root, NoneNotWrapped, applevel
from pypy.interpreter.gateway import interp2app, ObjSpace
from pypy.interpreter.typedef import TypeDef, make_weakref_descr
from pypy.interpreter.argument import Arguments
from pypy.interpreter.baseobjspace import Wrappable
from pypy.rlib.rarithmetic import r_uint, intmask
from pypy.rlib.objectmodel import compute_identity_hash
from pypy.rlib.debug import make_sure_not_resized
from pypy.rlib import jit


def raise_type_err(space, argument, expected, w_obj):
    type_name = space.type(w_obj).getname(space, '?')
    raise operationerrfmt(space.w_TypeError,
                          "argument %s must be %s, not %s",
                          argument, expected, type_name)

def unwrap_attr(space, w_attr):
    try:
        return space.str_w(w_attr)
    except OperationError, e:
        if not e.match(space, space.w_TypeError):
            raise
        return "?"    # any string different from "__dict__" & co. is fine
        # XXX it's not clear that we have to catch the TypeError...

def descr_classobj_new(space, w_subtype, w_name, w_bases, w_dict):
    if not space.is_true(space.isinstance(w_bases, space.w_tuple)):
        raise_type_err(space, 'bases', 'tuple', w_bases)
    
    if not space.is_true(space.isinstance(w_dict, space.w_dict)):
        raise_type_err(space, 'bases', 'tuple', w_bases)

    if not space.is_true(space.contains(w_dict, space.wrap("__doc__"))):
        space.setitem(w_dict, space.wrap("__doc__"), space.w_None)

    # XXX missing: lengthy and obscure logic about "__module__"
        
    bases_w = space.fixedview(w_bases)
    for w_base in bases_w:
        if not isinstance(w_base, W_ClassObject):
            w_metaclass = space.type(w_base)
            if space.is_true(space.callable(w_metaclass)):
                return space.call_function(w_metaclass, w_name,
                                           w_bases, w_dict)
            raise OperationError(space.w_TypeError,
                                 space.wrap("base must be class"))

    return W_ClassObject(space, w_name, bases_w, w_dict)

class W_ClassObject(Wrappable):
    def __init__(self, space, w_name, bases, w_dict):
        self.name = space.str_w(w_name)
        make_sure_not_resized(bases)
        self.bases_w = bases
        self.w_dict = w_dict
 
    def getdict(self):
        return self.w_dict

    def setdict(self, space, w_dict):
        if not space.is_true(space.isinstance(w_dict, space.w_dict)):
            raise OperationError(
                space.w_TypeError,
                space.wrap("__dict__ must be a dictionary object"))
        self.w_dict = w_dict

    def setname(self, space, w_newname):
        if not space.is_true(space.isinstance(w_newname, space.w_str)):
            raise OperationError(
                    space.w_TypeError,
                    space.wrap("__name__ must be a string object"))
        self.name = space.str_w(w_newname)

    def setbases(self, space, w_bases):
        # XXX in theory, this misses a check against inheritance cycles
        # although on pypy we don't get a segfault for infinite
        # recursion anyway 
        if not space.is_true(space.isinstance(w_bases, space.w_tuple)):
            raise OperationError(
                    space.w_TypeError,
                    space.wrap("__bases__ must be a tuple object"))
        bases_w = space.fixedview(w_bases)
        for w_base in bases_w:
            if not isinstance(w_base, W_ClassObject):
                raise OperationError(space.w_TypeError,
                                     space.wrap("__bases__ items must be classes"))
        self.bases_w = bases_w

    def is_subclass_of(self, other):
        assert isinstance(other, W_ClassObject)
        if self is other:
            return True
        for base in self.bases_w:
            assert isinstance(base, W_ClassObject)
            if base.is_subclass_of(other):
                return True
        return False

    @jit.unroll_safe
    def lookup(self, space, w_attr):
        # returns w_value or interplevel None
        w_result = space.finditem(self.w_dict, w_attr)
        if w_result is not None:
            return w_result
        for base in self.bases_w:
            # XXX fix annotation of bases_w to be a list of W_ClassObjects
            assert isinstance(base, W_ClassObject)
            w_result = base.lookup(space, w_attr)
            if w_result is not None:
                return w_result
        return None

    def descr_getattribute(self, space, w_attr):
        name = unwrap_attr(space, w_attr)
        if name and name[0] == "_":
            if name == "__dict__":
                return self.w_dict
            elif name == "__name__":
                return space.wrap(self.name)
            elif name == "__bases__":
                return space.newtuple(self.bases_w)
        w_value = self.lookup(space, w_attr)
        if w_value is None:
            raise operationerrfmt(
                space.w_AttributeError,
                "class %s has no attribute '%s'",
                self.name, name)

        w_descr_get = space.lookup(w_value, '__get__')
        if w_descr_get is None:
            return w_value
        return space.call_function(w_descr_get, w_value, space.w_None, self)

    def descr_setattr(self, space, w_attr, w_value):
        name = unwrap_attr(space, w_attr)
        if name and name[0] == "_":
            if name == "__dict__":
                self.setdict(space, w_value)
                return
            elif name == "__name__":
                self.setname(space, w_value)
                return
            elif name == "__bases__":
                self.setbases(space, w_value)
                return
            elif name == "__del__":
                if self.lookup(space, w_attr) is None:
                    msg = ("a __del__ method added to an existing class "
                           "will not be called")
                    space.warn(msg, space.w_RuntimeWarning)
        space.setitem(self.w_dict, w_attr, w_value)

    def descr_delattr(self, space, w_attr):
        name = unwrap_attr(space, w_attr)
        if name in ("__dict__", "__name__", "__bases__"):
            raise operationerrfmt(
                space.w_TypeError,
                "cannot delete attribute '%s'", name)
        try:
            space.delitem(self.w_dict, w_attr)
        except OperationError, e:
            if not e.match(space, space.w_KeyError):
                raise
            raise operationerrfmt(
                space.w_AttributeError,
                "class %s has no attribute '%s'",
                self.name, name)

    def descr_repr(self, space):
        mod = self.get_module_string(space)
        return self.getrepr(space, "class %s.%s" % (mod, self.name))

    def descr_str(self, space):
        mod = self.get_module_string(space)
        if mod == "?":
            return space.wrap(self.name)
        else:
            return space.wrap("%s.%s" % (mod, self.name))

    def get_module_string(self, space):
        try:
            w_mod = self.descr_getattribute(space, space.wrap("__module__"))
        except OperationError, e:
            if not e.match(space, space.w_AttributeError):
                raise
            return "?"
        if space.is_true(space.isinstance(w_mod, space.w_str)):
            return space.str_w(w_mod)
        return "?"

    def __repr__(self):
        # NOT_RPYTHON
        return '<W_ClassObject(%s)>' % self.name

def class_descr_call(space, w_self, __args__):
    self = space.interp_w(W_ClassObject, w_self)
    if self.lookup(space, space.wrap('__del__')) is not None:
        w_inst = W_InstanceObjectWithDel(space, self)
    else:
        w_inst = W_InstanceObject(space, self)
    w_init = w_inst.getattr(space, space.wrap('__init__'), False)
    if w_init is not None:
        w_result = space.call_args(w_init, __args__)
        if not space.is_w(w_result, space.w_None):
            raise OperationError(
                space.w_TypeError,
                space.wrap("__init__() should return None"))
    elif __args__.arguments_w or __args__.keywords:
        raise OperationError(
                space.w_TypeError,
                space.wrap("this constructor takes no arguments"))
    return w_inst

W_ClassObject.typedef = TypeDef("classobj",
    __new__ = interp2app(descr_classobj_new),
    __repr__ = interp2app(W_ClassObject.descr_repr,
                          unwrap_spec=['self', ObjSpace]),
    __str__ = interp2app(W_ClassObject.descr_str,
                         unwrap_spec=['self', ObjSpace]),
    __call__ = interp2app(class_descr_call,
                          unwrap_spec=[ObjSpace, W_Root, Arguments]),
    __getattribute__ = interp2app(W_ClassObject.descr_getattribute,
                             unwrap_spec=['self', ObjSpace, W_Root]),
    __setattr__ = interp2app(W_ClassObject.descr_setattr,
                             unwrap_spec=['self', ObjSpace, W_Root, W_Root]),
    __delattr__ = interp2app(W_ClassObject.descr_delattr,
                             unwrap_spec=['self', ObjSpace, W_Root]),
)
W_ClassObject.typedef.acceptable_as_base_class = False


def make_unary_instance_method(name):
    def unaryop(self, space):
        w_meth = self.getattr(space, space.wrap(name), True)
        return space.call_function(w_meth)
    unaryop.func_name = name
    return unaryop

def make_binary_returning_notimplemented_instance_method(name):
    def binaryop(self, space, w_other):
        try:
            w_meth = self.getattr(space, space.wrap(name), False)
        except OperationError, e:
            if e.match(space, space.w_AttributeError):
                return space.w_NotImplemented
            raise
        else:
            if w_meth is None:
                return space.w_NotImplemented
            return space.call_function(w_meth, w_other)
    binaryop.func_name = name
    return binaryop

def make_binary_instance_method(name):
    specialname = "__%s__" % (name, )
    rspecialname = "__r%s__" % (name, )
    objspacename = name
    if name in ['and', 'or']:
        objspacename = name + '_'

    def binaryop(self, space, w_other):
        w_a, w_b = _coerce_helper(space, self, w_other)
        if w_a is None:
            w_a = self
            w_b = w_other
        if w_a is self:
            w_meth = self.getattr(space, space.wrap(specialname), False)
            if w_meth is None:
                return space.w_NotImplemented
            return space.call_function(w_meth, w_b)
        else:
            return getattr(space, objspacename)(w_a, w_b)
    binaryop.func_name = name

    def rbinaryop(self, space, w_other):
        w_a, w_b = _coerce_helper(space, self, w_other)
        if w_a is None or w_a is self:
            w_meth = self.getattr(space, space.wrap(rspecialname), False)
            if w_meth is None:
                return space.w_NotImplemented
            return space.call_function(w_meth, w_other)
        else:
            return getattr(space, objspacename)(w_b, w_a)
    rbinaryop.func_name = "r" + name
    return binaryop, rbinaryop

def _coerce_helper(space, w_self, w_other):
    try:
        w_tup = space.coerce(w_self, w_other)
    except OperationError, e:
        if not e.match(space, space.w_TypeError):
            raise
        return [None, None]
    return space.fixedview(w_tup, 2)

def descr_instance_new(space, w_type, w_class, w_dict=None):
    # w_type is not used at all
    if not isinstance(w_class, W_ClassObject):
        raise OperationError(
            space.w_TypeError,
            space.wrap("instance() first arg must be class"))
    if space.is_w(w_dict, space.w_None):
        w_dict = None
    elif not space.is_true(space.isinstance(w_dict, space.w_dict)):
        raise OperationError(
            space.w_TypeError,
            space.wrap("instance() second arg must be dictionary or None"))
    return W_InstanceObject(space, w_class, w_dict)

class W_InstanceObject(Wrappable):
    def __init__(self, space, w_class, w_dict=None):
        if w_dict is None:
            w_dict = space.newdict(instance=True)
        assert isinstance(w_class, W_ClassObject)
        self.w_class = w_class
        self.w_dict = w_dict
        self.space = space

    def getdict(self):
        return self.w_dict

    def setdict(self, space, w_dict):
        if (w_dict is None or
            not space.is_true(space.isinstance(w_dict, space.w_dict))):
            raise OperationError(
                space.w_TypeError,
                space.wrap("__dict__ must be a dictionary object"))
        self.w_dict = w_dict

    def setclass(self, space, w_class):
        if w_class is None or not isinstance(w_class, W_ClassObject):
            raise OperationError(
                space.w_TypeError,
                space.wrap("__class__ must be set to a class"))
        self.w_class = w_class


    def getattr(self, space, w_name, exc=True):
        w_result = space.finditem(self.w_dict, w_name)
        if w_result is not None:
            return w_result
        w_value = self.w_class.lookup(space, w_name)
        if w_value is None:
            if exc:
                raise operationerrfmt(
                    space.w_AttributeError,
                    "%s instance has no attribute '%s'",
                    self.w_class.name, space.str_w(w_name))
            else:
                return None
        w_descr_get = space.lookup(w_value, '__get__')
        if w_descr_get is None:
            return w_value
        return space.call_function(w_descr_get, w_value, self, self.w_class)

    def descr_getattribute(self, space, w_attr):
        name = space.str_w(w_attr)
        if len(name) >= 8 and name[0] == '_':
            if name == "__dict__":
                return self.w_dict
            elif name == "__class__":
                return self.w_class
        try:
            return self.getattr(space, w_attr)
        except OperationError, e:
            if not e.match(space, space.w_AttributeError):
                raise
            w_meth = self.getattr(space, space.wrap('__getattr__'), False)
            if w_meth is not None:
                return space.call_function(w_meth, w_attr)
            raise

    def descr_setattr(self, space, w_name, w_value):
        name = unwrap_attr(space, w_name)
        w_meth = self.getattr(space, space.wrap('__setattr__'), False)
        if name and name[0] == "_":
            if name == '__dict__':
                self.setdict(space, w_value)
                return
            if name == '__class__':
                self.setclass(space, w_value)
                return
            if name == '__del__' and w_meth is None:
                if (not isinstance(self, W_InstanceObjectWithDel)
                    and space.finditem(self.w_dict, w_name) is None):
                    msg = ("a __del__ method added to an instance "
                           "with no __del__ in the class will not be called")
                    space.warn(msg, space.w_RuntimeWarning)
        if w_meth is not None:
            space.call_function(w_meth, w_name, w_value)
        else:
            self.setdictvalue(space, name, w_value)

    def descr_delattr(self, space, w_name):
        name = unwrap_attr(space, w_name)
        if name and name[0] == "_":
            if name == '__dict__':
                # use setdict to raise the error
                self.setdict(space, None)
                return
            elif name == '__class__':
                # use setclass to raise the error
                self.setclass(space, None)
                return
        w_meth = self.getattr(space, space.wrap('__delattr__'), False)
        if w_meth is not None:
            space.call_function(w_meth, w_name)
        else:
            if not self.deldictvalue(space, w_name):
                raise operationerrfmt(
                    space.w_AttributeError,
                    "%s instance has no attribute '%s'",
                    self.w_class.name, name)

    def descr_repr(self, space):
        w_meth = self.getattr(space, space.wrap('__repr__'), False)
        if w_meth is None:
            w_class = self.w_class
            mod = w_class.get_module_string(space)
            return self.getrepr(space, "%s.%s instance" % (mod, w_class.name))
        return space.call_function(w_meth)

    def descr_str(self, space):
        w_meth = self.getattr(space, space.wrap('__str__'), False)
        if w_meth is None:
            return self.descr_repr(space)
        return space.call_function(w_meth)

    def descr_unicode(self, space):
        w_meth = self.getattr(space, space.wrap('__unicode__'), False)
        if w_meth is None:
            return self.descr_str(space)
        return space.call_function(w_meth)

    def descr_len(self, space):
        w_meth = self.getattr(space, space.wrap('__len__'))
        w_result = space.call_function(w_meth)
        if space.is_true(space.isinstance(w_result, space.w_int)):
            if space.is_true(space.lt(w_result, space.wrap(0))):
                raise OperationError(
                    space.w_ValueError,
                    space.wrap("__len__() should return >= 0"))
            return w_result
        raise OperationError(
            space.w_TypeError,
            space.wrap("__len__() should return an int"))

    def descr_getitem(self, space, w_key):
        w_meth = self.getattr(space, space.wrap('__getitem__'))
        return space.call_function(w_meth, w_key)

    def descr_setitem(self, space, w_key, w_value):
        w_meth = self.getattr(space, space.wrap('__setitem__'))
        space.call_function(w_meth, w_key, w_value)

    def descr_delitem(self, space, w_key):
        w_meth = self.getattr(space, space.wrap('__delitem__'))
        space.call_function(w_meth, w_key)

    def descr_iter(self, space):
        w_meth = self.getattr(space, space.wrap('__iter__'), False)
        if w_meth is not None:
            return space.call_function(w_meth)
        w_meth = self.getattr(space, space.wrap('__getitem__'), False)
        if w_meth is None:
            raise OperationError(
                space.w_TypeError,
                space.wrap("iteration over non-sequence"))
        return space.newseqiter(self)
    #XXX do I really need a next method? the old implementation had one, but I
    # don't see the point

    def descr_getslice(self, space, w_i, w_j):
        w_meth = self.getattr(space, space.wrap('__getslice__'), False)
        if w_meth is not None:
            return space.call_function(w_meth, w_i, w_j)
        else:
            return space.getitem(self, space.newslice(w_i, w_j, space.w_None))

    def descr_setslice(self, space, w_i, w_j, w_sequence):
        w_meth = self.getattr(space, space.wrap('__setslice__'), False)
        if w_meth is not None:
            space.call_function(w_meth, w_i, w_j, w_sequence)
        else:
            space.setitem(self, space.newslice(w_i, w_j, space.w_None),
                          w_sequence)

    def descr_delslice(self, space, w_i, w_j):
        w_meth = self.getattr(space, space.wrap('__delslice__'), False)
        if w_meth is not None:
            space.call_function(w_meth, w_i, w_j)
        else:
            return space.delitem(self, space.newslice(w_i, w_j, space.w_None))

    def descr_call(self, space, __args__):
        w_meth = self.getattr(space, space.wrap('__call__'))
        return space.call_args(w_meth, __args__)

    def descr_nonzero(self, space):
        w_func = self.getattr(space, space.wrap('__nonzero__'), False)
        if w_func is None:
            w_func = self.getattr(space, space.wrap('__len__'), False)
            if w_func is None:
                return space.w_True
        w_result = space.call_function(w_func)
        if space.is_true(space.isinstance(w_result, space.w_int)):
            if space.is_true(space.lt(w_result, space.wrap(0))):
                raise OperationError(
                    space.w_ValueError,
                    space.wrap("__nonzero__() should return >= 0"))
            return w_result
        raise OperationError(
            space.w_TypeError,
            space.wrap("__nonzero__() should return an int"))

    def descr_cmp(self, space, w_other): # do all the work here like CPython
        w_a, w_b = _coerce_helper(space, self, w_other)
        if w_a is None:
            w_a = self
            w_b = w_other
        else:
            if (not isinstance(w_a, W_InstanceObject) and
                not isinstance(w_b, W_InstanceObject)):
                return space.cmp(w_a, w_b)
        if isinstance(w_a, W_InstanceObject):
            w_func = w_a.getattr(space, space.wrap('__cmp__'), False)
            if w_func is not None:
                w_res = space.call_function(w_func, w_b)
                if space.is_w(w_res, space.w_NotImplemented):
                    return w_res
                try:
                    res = space.int_w(w_res)
                except OperationError, e:
                    if e.match(space, space.w_TypeError):
                        raise OperationError(
                            space.w_TypeError,
                            space.wrap("__cmp__ must return int"))
                    raise
                if res > 0:
                    return space.wrap(1)
                if res < 0:
                    return space.wrap(-1)
                return space.wrap(0)
        if isinstance(w_b, W_InstanceObject):
            w_func = w_b.getattr(space, space.wrap('__cmp__'), False)
            if w_func is not None:
                w_res = space.call_function(w_func, w_a)
                if space.is_w(w_res, space.w_NotImplemented):
                    return w_res
                try:
                    res = space.int_w(w_res)
                except OperationError, e:
                    if e.match(space, space.w_TypeError):
                        raise OperationError(
                            space.w_TypeError,
                            space.wrap("__cmp__ must return int"))
                    raise
                if res < 0:
                    return space.wrap(1)
                if res > 0:
                    return space.wrap(-1)
                return space.wrap(0)
        return space.w_NotImplemented

    def descr_hash(self, space):
        w_func = self.getattr(space, space.wrap('__hash__'), False)
        if w_func is None:
            w_eq =  self.getattr(space, space.wrap('__eq__'), False)
            w_cmp =  self.getattr(space, space.wrap('__cmp__'), False)
            if w_eq is not None or w_cmp is not None:
                raise OperationError(space.w_TypeError,
                                     space.wrap("unhashable instance"))
            else:
                return space.wrap(compute_identity_hash(self))
        w_ret = space.call_function(w_func)
        if (not space.is_true(space.isinstance(w_ret, space.w_int)) and
            not space.is_true(space.isinstance(w_ret, space.w_long))):
            raise OperationError(
                space.w_TypeError,
                space.wrap("__hash__ must return int or long"))
        return w_ret

    def descr_index(self, space):
        w_func = self.getattr(space, space.wrap('__index__'), False)
        if w_func is not None:
            return space.call_function(w_func)
        raise OperationError(
            space.w_TypeError,
            space.wrap("object cannot be interpreted as an index"))

    def descr_contains(self, space, w_obj):
        w_func = self.getattr(space, space.wrap('__contains__'), False)
        if w_func is not None:
            return space.wrap(space.is_true(space.call_function(w_func, w_obj)))
        # now do it ourselves
        w_iter = space.iter(self)
        while 1:
            try:
                w_x = space.next(w_iter)
            except OperationError, e:
                if e.match(space, space.w_StopIteration):
                    return space.w_False
                raise
            if space.eq_w(w_x, w_obj):
                return space.w_True


    def descr_pow(self, space, w_other, w_modulo=None):
        if space.is_w(w_modulo, space.w_None):
            w_a, w_b = _coerce_helper(space, self, w_other)
            if w_a is None:
                w_a = self
                w_b = w_other
            if w_a is self:
                w_func = self.getattr(space, space.wrap('__pow__'), False)
                if w_func is not None:
                    return space.call_function(w_func, w_other)
                return space.w_NotImplemented
            else:
                return space.pow(w_a, w_b, space.w_None)
        else:
            # CPython also doesn't try coercion in this case
            w_func = self.getattr(space, space.wrap('__pow__'), False)
            if w_func is not None:
                return space.call_function(w_func, w_other, w_modulo)
            return space.w_NotImplemented

    def descr_rpow(self, space, w_other, w_modulo=None):
        if space.is_w(w_modulo, space.w_None):
            w_a, w_b = _coerce_helper(space, self, w_other)
            if w_a is None:
                w_a = self
                w_b = w_other
            if w_a is self:
                w_func = self.getattr(space, space.wrap('__rpow__'), False)
                if w_func is not None:
                    return space.call_function(w_func, w_other)
                return space.w_NotImplemented
            else:
                return space.pow(w_b, w_a, space.w_None)
        else:
            # CPython also doesn't try coercion in this case
            w_func = self.getattr(space, space.wrap('__rpow__'), False)
            if w_func is not None:
                return space.call_function(w_func, w_other, w_modulo)
            return space.w_NotImplemented

    def descr_next(self, space):
        w_func = self.getattr(space, space.wrap('next'), False)
        if w_func is None:
            raise OperationError(space.w_TypeError,
                                 space.wrap("instance has no next() method"))
        return space.call_function(w_func)

    def descr_del(self, space):
        # Note that this is called from executioncontext.UserDelAction
        # via the space.userdel() method.
        w_func = self.getattr(space, space.wrap('__del__'), False)
        if w_func is not None:
            space.call_function(w_func)

rawdict = {}

# unary operations
for op in "neg pos abs invert int long float oct hex".split():
    specialname = "__%s__" % (op, )
    # fool the gateway logic by giving it a real unbound method
    meth = new.instancemethod(
        make_unary_instance_method(specialname),
        None,
        W_InstanceObject)
    rawdict[specialname] = interp2app(
        meth,
        unwrap_spec=["self", ObjSpace])

# binary operations that return NotImplemented if they fail
# e.g. rich comparisons, coerce and inplace ops
for op in 'eq ne gt lt ge le coerce imod iand ipow itruediv ilshift ixor irshift ifloordiv idiv isub imul iadd ior'.split():
    specialname = "__%s__" % (op, )
    # fool the gateway logic by giving it a real unbound method
    meth = new.instancemethod(
        make_binary_returning_notimplemented_instance_method(specialname),
        None,
        W_InstanceObject)
    rawdict[specialname] = interp2app(
        meth,
        unwrap_spec=["self", ObjSpace, W_Root])

for op in "or and xor lshift rshift add sub mul div mod divmod floordiv truediv".split():
    specialname = "__%s__" % (op, )
    rspecialname = "__r%s__" % (op, )
    func, rfunc = make_binary_instance_method(op)
    # fool the gateway logic by giving it a real unbound method
    meth = new.instancemethod(func, None, W_InstanceObject)
    rawdict[specialname] = interp2app(
        meth,
        unwrap_spec=["self", ObjSpace, W_Root])
    rmeth = new.instancemethod(rfunc, None, W_InstanceObject)
    rawdict[rspecialname] = interp2app(
        rmeth,
        unwrap_spec=["self", ObjSpace, W_Root])

W_InstanceObject.typedef = TypeDef("instance",
    __new__ = interp2app(descr_instance_new),
    __getattribute__ = interp2app(W_InstanceObject.descr_getattribute,
                                  unwrap_spec=['self', ObjSpace, W_Root]),
    __setattr__ = interp2app(W_InstanceObject.descr_setattr,
                             unwrap_spec=['self', ObjSpace, W_Root, W_Root]),
    __delattr__ = interp2app(W_InstanceObject.descr_delattr,
                             unwrap_spec=['self', ObjSpace, W_Root]),
    __repr__ = interp2app(W_InstanceObject.descr_repr,
                          unwrap_spec=['self', ObjSpace]),
    __str__ = interp2app(W_InstanceObject.descr_str,
                         unwrap_spec=['self', ObjSpace]),
    __unicode__ = interp2app(W_InstanceObject.descr_unicode,
                         unwrap_spec=['self', ObjSpace]),
    __len__ = interp2app(W_InstanceObject.descr_len,
                         unwrap_spec=['self', ObjSpace]),
    __getitem__ = interp2app(W_InstanceObject.descr_getitem,
                             unwrap_spec=['self', ObjSpace, W_Root]),
    __setitem__ = interp2app(W_InstanceObject.descr_setitem,
                             unwrap_spec=['self', ObjSpace, W_Root, W_Root]),
    __delitem__ = interp2app(W_InstanceObject.descr_delitem,
                             unwrap_spec=['self', ObjSpace, W_Root]),
    __iter__ = interp2app(W_InstanceObject.descr_iter,
                          unwrap_spec=['self', ObjSpace]),
    __getslice__ = interp2app(W_InstanceObject.descr_getslice,
                             unwrap_spec=['self', ObjSpace, W_Root, W_Root]),
    __setslice__ = interp2app(W_InstanceObject.descr_setslice,
                             unwrap_spec=['self', ObjSpace, W_Root,
                                          W_Root, W_Root]),
    __delslice__ = interp2app(W_InstanceObject.descr_delslice,
                             unwrap_spec=['self', ObjSpace, W_Root, W_Root]),
    __call__ = interp2app(W_InstanceObject.descr_call,
                          unwrap_spec=['self', ObjSpace, Arguments]),
    __nonzero__ = interp2app(W_InstanceObject.descr_nonzero,
                             unwrap_spec=['self', ObjSpace]),
    __cmp__ = interp2app(W_InstanceObject.descr_cmp,
                         unwrap_spec=['self', ObjSpace, W_Root]),
    __hash__ = interp2app(W_InstanceObject.descr_hash,
                          unwrap_spec=['self', ObjSpace]),
    __index__ = interp2app(W_InstanceObject.descr_index,
                           unwrap_spec=['self', ObjSpace]),
    __contains__ = interp2app(W_InstanceObject.descr_contains,
                         unwrap_spec=['self', ObjSpace, W_Root]),
    __pow__ = interp2app(W_InstanceObject.descr_pow,
                         unwrap_spec=['self', ObjSpace, W_Root, W_Root]),
    __rpow__ = interp2app(W_InstanceObject.descr_rpow,
                         unwrap_spec=['self', ObjSpace, W_Root, W_Root]),
    next = interp2app(W_InstanceObject.descr_next,
                      unwrap_spec=['self', ObjSpace]),
    __weakref__ = make_weakref_descr(W_InstanceObject),
    __del__ = interp2app(W_InstanceObject.descr_del,
                         unwrap_spec=['self', ObjSpace]),
    **rawdict
)

class W_InstanceObjectWithDel(W_InstanceObject):
    def __del__(self):
        self._enqueue_for_destruction(self.space)
