"""
Implementation of the 'abstract instance and subclasses' protocol:
objects can return pseudo-classes as their '__class__' attribute, and
pseudo-classes can have a '__bases__' attribute with a tuple of other
pseudo-classes.  The standard built-in functions isinstance() and
issubclass() follow and trust these attributes is they are present, in
addition to checking for instances and subtypes in the normal way.
"""

from rpython.rlib import jit

from pypy.interpreter.baseobjspace import ObjSpace as BaseObjSpace
from pypy.interpreter.error import OperationError
from pypy.module.__builtin__.interp_classobj import W_ClassObject
from pypy.module.__builtin__.interp_classobj import W_InstanceObject


def _get_bases(space, w_cls):
    """Returns 'cls.__bases__'.  Returns None if there is
    no __bases__ or if cls.__bases__ is not a tuple.
    """
    try:
        w_bases = space.getattr(w_cls, space.wrap('__bases__'))
    except OperationError as e:
        if not e.match(space, space.w_AttributeError):
            raise       # propagate other errors
        return None
    if space.isinstance_w(w_bases, space.w_tuple):
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
    except OperationError as e:
        if not e.match(space, space.w_AttributeError):
            raise       # propagate other errors
        return space.type(w_obj)


# ---------- isinstance ----------


def p_recursive_isinstance_w(space, w_inst, w_cls):
    # Copied straight from CPython 2.7.  Does not handle 'cls' being a tuple.
    if (isinstance(w_cls, W_ClassObject) and
        isinstance(w_inst, W_InstanceObject)):
        return w_inst.w_class.is_subclass_of(w_cls)

    if space.isinstance_w(w_cls, space.w_type):
        return p_recursive_isinstance_type_w(space, w_inst, w_cls)

    check_class(space, w_cls, "isinstance() arg 2 must be a class, type,"
                              " or tuple of classes and types")
    try:
        w_abstractclass = space.getattr(w_inst, space.wrap('__class__'))
    except OperationError as e:
        if e.async(space):      # ignore most exceptions
            raise
        return False
    else:
        return p_abstract_issubclass_w(space, w_abstractclass, w_cls)


def p_recursive_isinstance_type_w(space, w_inst, w_type):
    # subfunctionality of p_recursive_isinstance_w(): assumes that w_type is
    # a type object.  Copied straight from CPython 2.7.
    if space.isinstance_w(w_inst, w_type):
        return True
    try:
        w_abstractclass = space.getattr(w_inst, space.wrap('__class__'))
    except OperationError as e:
        if e.async(space):      # ignore most exceptions
            raise
    else:
        if w_abstractclass is not space.type(w_inst):
            if space.isinstance_w(w_abstractclass, space.w_type):
                return space.issubtype_w(w_abstractclass, w_type)
    return False


@jit.unroll_safe
def abstract_isinstance_w(space, w_obj, w_klass_or_tuple, allow_override=False):
    """Implementation for the full 'isinstance(obj, klass_or_tuple)'."""
    # Copied from CPython 2.7's PyObject_Isinstance().  Additionally,
    # if 'allow_override' is False (the default), then don't try to
    # use a custom __instancecheck__ method.

    # WARNING: backward compatibility function name here.  CPython
    # uses the name "abstract" to refer to the logic of handling
    # class-like objects, with a "__bases__" attribute.  This function
    # here is not related to that and implements the full
    # PyObject_IsInstance() logic.

    # Quick test for an exact match
    # disabled with jit to make it not impose a strong type condition
    if not jit.we_are_jitted() and space.type(w_obj) is w_klass_or_tuple:
        return True

    # -- case (anything, tuple)
    # XXX it might be risky that the JIT sees this
    if space.isinstance_w(w_klass_or_tuple, space.w_tuple):
        for w_klass in space.fixedview(w_klass_or_tuple):
            if abstract_isinstance_w(space, w_obj, w_klass, allow_override):
                return True
        return False

    # -- case (anything, type)
    if allow_override:
        w_check = space.lookup(w_klass_or_tuple, "__instancecheck__")
        if w_check is not None:
            # this is the common case: all type objects have a method
            # __instancecheck__.  The one in the base 'type' type calls
            # back p_recursive_isinstance_type_w() from the present module.
            return space.is_true(space.get_and_call_function(
                w_check, w_klass_or_tuple, w_obj))

    return p_recursive_isinstance_w(space, w_obj, w_klass_or_tuple)


# ---------- issubclass ----------


@jit.unroll_safe
def p_abstract_issubclass_w(space, w_derived, w_cls):
    # Copied straight from CPython 2.7, function abstract_issubclass().
    # Don't confuse this with the function abstract_issubclass_w() below.
    # Here, w_cls cannot be a tuple.
    while True:
        if space.is_w(w_derived, w_cls):
            return True
        w_bases = _get_bases(space, w_derived)
        if w_bases is None:
            return False
        bases_w = space.fixedview(w_bases)
        last_index = len(bases_w) - 1
        if last_index < 0:
            return False
        # Avoid recursivity in the single inheritance case; in general,
        # don't recurse on the last item in the tuple (loop instead).
        for i in range(last_index):
            if p_abstract_issubclass_w(space, bases_w[i], w_cls):
                return True
        w_derived = bases_w[last_index]


def p_recursive_issubclass_w(space, w_derived, w_cls):
    # From CPython's function of the same name (which as far as I can tell
    # is not recursive).  Copied straight from CPython 2.7.
    if (space.isinstance_w(w_cls, space.w_type) and
        space.isinstance_w(w_derived, space.w_type)):
        return space.issubtype_w(w_derived, w_cls)
    #
    if (isinstance(w_derived, W_ClassObject) and
        isinstance(w_cls, W_ClassObject)):
        return w_derived.is_subclass_of(w_cls)
    #
    check_class(space, w_derived, "issubclass() arg 1 must be a class")
    check_class(space, w_cls, "issubclass() arg 2 must be a class"
                              " or tuple of classes")
    return p_abstract_issubclass_w(space, w_derived, w_cls)


@jit.unroll_safe
def abstract_issubclass_w(space, w_derived, w_klass_or_tuple,
                          allow_override=False):
    """Implementation for the full 'issubclass(derived, klass_or_tuple)'."""

    # WARNING: backward compatibility function name here.  CPython
    # uses the name "abstract" to refer to the logic of handling
    # class-like objects, with a "__bases__" attribute.  This function
    # here is not related to that and implements the full
    # PyObject_IsSubclass() logic.  There is also p_abstract_issubclass_w().

    # -- case (anything, tuple-of-classes)
    if space.isinstance_w(w_klass_or_tuple, space.w_tuple):
        for w_klass in space.fixedview(w_klass_or_tuple):
            if abstract_issubclass_w(space, w_derived, w_klass, allow_override):
                return True
        return False

    # -- case (anything, type)
    if allow_override:
        w_check = space.lookup(w_klass_or_tuple, "__subclasscheck__")
        if w_check is not None:
            # this is the common case: all type objects have a method
            # __subclasscheck__.  The one in the base 'type' type calls
            # back p_recursive_issubclass_w() from the present module.
            return space.is_true(space.get_and_call_function(
                w_check, w_klass_or_tuple, w_derived))

    return p_recursive_issubclass_w(space, w_derived, w_klass_or_tuple)


# ------------------------------------------------------------
# Exception helpers

def exception_is_valid_obj_as_class_w(space, w_obj):
    if isinstance(w_obj, W_ClassObject):
        return True
    return BaseObjSpace.exception_is_valid_obj_as_class_w(space, w_obj)

def exception_is_valid_class_w(space, w_cls):
    if isinstance(w_cls, W_ClassObject):
        return True
    return BaseObjSpace.exception_is_valid_class_w(space, w_cls)

def exception_getclass(space, w_obj):
    if isinstance(w_obj, W_InstanceObject):
        return w_obj.w_class
    return BaseObjSpace.exception_getclass(space, w_obj)

def exception_issubclass_w(space, w_cls1, w_cls2):
    if isinstance(w_cls1, W_ClassObject):
        if isinstance(w_cls2, W_ClassObject):
            return w_cls1.is_subclass_of(w_cls2)
        return False
    if isinstance(w_cls2, W_ClassObject):
        return False
    return BaseObjSpace.exception_issubclass_w(space, w_cls1, w_cls2)

# ____________________________________________________________
# App-level interface

def issubclass(space, w_cls, w_klass_or_tuple):
    """Check whether a class 'cls' is a subclass (i.e., a derived class) of
another class.  When using a tuple as the second argument, check whether
'cls' is a subclass of any of the classes listed in the tuple."""
    result = abstract_issubclass_w(space, w_cls, w_klass_or_tuple, True)
    return space.wrap(result)

def isinstance(space, w_obj, w_klass_or_tuple):
    """Check whether an object is an instance of a class (or of a subclass
thereof).  When using a tuple as the second argument, check whether 'obj'
is an instance of any of the classes listed in the tuple."""
    result = abstract_isinstance_w(space, w_obj, w_klass_or_tuple, True)
    return space.wrap(result)

# avoid namespace pollution
app_issubclass = issubclass; del issubclass
app_isinstance = isinstance; del isinstance
