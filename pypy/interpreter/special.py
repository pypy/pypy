from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import oefmt


class Ellipsis(W_Root):

    @staticmethod
    def descr_new_ellipsis(space, w_type):
        return space.w_Ellipsis

    def descr__repr__(self, space):
        return space.newtext('Ellipsis')

    descr__reduce__ = descr__repr__


class NotImplemented(W_Root):

    @staticmethod
    def descr_new_notimplemented(space, w_type):
        return space.w_NotImplemented

    def descr__repr__(self, space):
        return space.newtext('NotImplemented')

    descr__reduce__ = descr__repr__

    def descr_bool(self, space):
        space.warn(
            space.newtext("NotImplemented should not be used in a boolean context"),
            space.w_DeprecationWarning
        )
        return space.w_True

class DisallowNew(W_Root):
    @staticmethod
    def descr_new_disallow(space, w_type, __args__):
        """Create and return a new object.  See help(type) for accurate signature."""
        name = w_type.getname(space)
        raise oefmt(space.w_TypeError, "cannot create '%s' instances", name)

class DisallowNewC(W_Root):
    @staticmethod
    def descr_new_disallow(space, w_type, __args__):
        """Create and return a new object.  See help(type) for accurate signature."""
        from pypy.module.cpyext.typeobject import W_PyCTypeObject
        if isinstance(w_type, W_PyCTypeObject):
            w_mod = w_type.get_module()
            if w_mod is None or not space.isinstance_w(w_mod, space.w_text):
                mod = 'builtins'
            else:
                mod = space.utf8_w(w_mod)
            name = mod + '.' + w_type.getname(space)
        else:
            name = w_type.getname(space)
        raise oefmt(space.w_TypeError, "cannot create '%s' instances", name)


