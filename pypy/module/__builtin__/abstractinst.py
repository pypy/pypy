"""
Implementation of the 'abstract instance and subclasses' protocol:
objects can return pseudo-classes as their '__class__' attribute, and
pseudo-classes can have a '__bases__' attribute with a tuple of other
pseudo-classes.  The standard built-in functions isinstance() and
issubclass() follow and trust these attributes is they are present, in
addition to checking for instances and subtypes in the normal way.
"""

from pypy.rlib import jit
from pypy.interpreter.error import OperationError
from pypy.module.__builtin__.interp_classobj import W_ClassObject
from pypy.module.__builtin__.interp_classobj import W_InstanceObject
from pypy.interpreter.baseobjspace import ObjSpace as BaseObjSpace

def _get_bases(space, w_cls):
    """Returns 'cls.__bases__'.  Returns None if there is
    no __bases__ or if cls.__bases__ is not a tuple.
    """
    try:
        w_bases = space.getattr(w_cls, space.wrap('__bases__'))
    except OperationError, e:
        if not e.match(space, space.w_AttributeError):
            raise       # propagate other errors
        return None
    if space.is_true(space.isinstance(w_bases, space.w_tuple)):
        return w_bases
    else:
        return None

def abstract_isclass_w(space, w_obj):
    return _get_bases(space, w_obj) is not None

def check_class(space, w_obj, msg):
    if not abstract_isclass_w(space, w_obj):
        raise OperationError(space.w_TypeError, space.wrap(msg))


def abstract_getclass(space, w_obj):
    try:
        return space.getattr(w_obj, space.wrap('__class__'))
    except OperationError, e:
        if not e.match(space, space.w_AttributeError):
            raise       # propagate other errors
        return space.type(w_obj)

@jit.unroll_safe
def abstract_isinstance_w(space, w_obj, w_klass_or_tuple):
    """Implementation for the full 'isinstance(obj, klass_or_tuple)'."""

    # -- case (anything, type)
    try:
        w_result = space.isinstance(w_obj, w_klass_or_tuple)
    except OperationError, e:   # if w_klass_or_tuple was not a type, ignore it
        if not e.match(space, space.w_TypeError):
            raise       # propagate other errors
    else:
        if space.is_true(w_result):
            return True
        # From now on we know that w_klass_or_tuple is indeed a type.
        # Try also to compare it with obj.__class__, if this is not
        # the same as type(obj).
        try:
            w_pretendtype = space.getattr(w_obj, space.wrap('__class__'))
            if space.is_w(w_pretendtype, space.type(w_obj)):
                return False     # common case: obj.__class__ is type(obj)
            w_result = space.issubtype(w_pretendtype, w_klass_or_tuple)
        except OperationError, e:
            if e.async(space):
                raise
            return False      # ignore most exceptions
        else:
            return space.is_true(w_result)

    # -- case (old-style instance, old-style class)
    oldstyleclass = space.interpclass_w(w_klass_or_tuple)
    if isinstance(oldstyleclass, W_ClassObject):
        oldstyleinst = space.interpclass_w(w_obj)
        if isinstance(oldstyleinst, W_InstanceObject):
            return oldstyleinst.w_class.is_subclass_of(oldstyleclass)
    # -- case (anything, tuple)
    # XXX it might be risky that the JIT sees this
    if space.is_true(space.isinstance(w_klass_or_tuple, space.w_tuple)):
        for w_klass in space.fixedview(w_klass_or_tuple):
            if abstract_isinstance_w(space, w_obj, w_klass):
                return True
        return False
    return _abstract_isinstance_w_helper(space, w_obj, w_klass_or_tuple)

@jit.dont_look_inside
def _abstract_isinstance_w_helper(space, w_obj, w_klass_or_tuple):

    # -- case (anything, abstract-class)
    check_class(space, w_klass_or_tuple,
                "isinstance() arg 2 must be a class, type,"
                " or tuple of classes and types")
    try:
        w_abstractclass = space.getattr(w_obj, space.wrap('__class__'))
    except OperationError, e:
        if e.async(space):      # ignore most exceptions
            raise
        return False
    else:
        return _issubclass_recurse(space, w_abstractclass, w_klass_or_tuple)


@jit.dont_look_inside
def _issubclass_recurse(space, w_derived, w_top):
    """Internal helper for abstract cases.  Here, w_top cannot be a tuple."""
    if space.is_w(w_derived, w_top):
        return True
    w_bases = _get_bases(space, w_derived)
    if w_bases is not None:
        for w_base in space.fixedview(w_bases):
            if _issubclass_recurse(space, w_base, w_top):
                return True
    return False


@jit.unroll_safe
def abstract_issubclass_w(space, w_derived, w_klass_or_tuple):
    """Implementation for the full 'issubclass(derived, klass_or_tuple)'."""

    # -- case (type, type)
    try:
        w_result = space.issubtype(w_derived, w_klass_or_tuple)
    except OperationError, e:   # if one of the args was not a type, ignore it
        if not e.match(space, space.w_TypeError):
            raise       # propagate other errors
    else:
        return space.is_true(w_result)

    # -- case (old-style class, old-style class)
    oldstylederived = space.interpclass_w(w_derived)
    if isinstance(oldstylederived, W_ClassObject):
        oldstyleklass = space.interpclass_w(w_klass_or_tuple)
        if isinstance(oldstyleklass, W_ClassObject):
            return oldstylederived.is_subclass_of(oldstyleklass)
    else:
        check_class(space, w_derived, "issubclass() arg 1 must be a class")
    # from here on, we are sure that w_derived is a class-like object

    # -- case (class-like-object, tuple-of-classes)
    # XXX it might be risky that the JIT sees this
    if space.is_true(space.isinstance(w_klass_or_tuple, space.w_tuple)):
        for w_klass in space.fixedview(w_klass_or_tuple):
            if abstract_issubclass_w(space, w_derived, w_klass):
                return True
        return False

    # -- case (class-like-object, abstract-class)
    check_class(space, w_klass_or_tuple,
                "issubclass() arg 2 must be a class, type,"
                " or tuple of classes and types")
    return _issubclass_recurse(space, w_derived, w_klass_or_tuple)

# ------------------------------------------------------------
# Exception helpers

def exception_is_valid_obj_as_class_w(space, w_obj):
    obj = space.interpclass_w(w_obj)
    if isinstance(obj, W_ClassObject):
        return True
    return BaseObjSpace.exception_is_valid_obj_as_class_w(space, w_obj)

def exception_is_valid_class_w(space, w_cls):
    cls = space.interpclass_w(w_cls)
    if isinstance(cls, W_ClassObject):
        return True
    return BaseObjSpace.exception_is_valid_class_w(space, w_cls)

def exception_getclass(space, w_obj):
    obj = space.interpclass_w(w_obj)
    if isinstance(obj, W_InstanceObject):
        return obj.w_class
    return BaseObjSpace.exception_getclass(space, w_obj)

def exception_issubclass_w(space, w_cls1, w_cls2):
    cls1 = space.interpclass_w(w_cls1)
    cls2 = space.interpclass_w(w_cls2)
    if isinstance(cls1, W_ClassObject):
        if isinstance(cls2, W_ClassObject):
            return cls1.is_subclass_of(cls2)
        return False
    if isinstance(cls2, W_ClassObject):
        return False
    return BaseObjSpace.exception_issubclass_w(space, w_cls1, w_cls2)

# ____________________________________________________________
# App-level interface

def issubclass(space, w_cls, w_klass_or_tuple):
    """Check whether a class 'cls' is a subclass (i.e., a derived class) of
another class.  When using a tuple as the second argument, check whether
'cls' is a subclass of any of the classes listed in the tuple."""
    return space.wrap(abstract_issubclass_w(space, w_cls, w_klass_or_tuple))

def isinstance(space, w_obj, w_klass_or_tuple):
    """Check whether an object is an instance of a class (or of a subclass
thereof).  When using a tuple as the second argument, check whether 'obj'
is an instance of any of the classes listed in the tuple."""
    return space.wrap(abstract_isinstance_w(space, w_obj, w_klass_or_tuple))

# avoid namespace pollution
app_issubclass = issubclass; del issubclass
app_isinstance = isinstance; del isinstance
