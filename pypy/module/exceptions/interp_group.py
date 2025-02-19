from pypy.module.exceptions.interp_exceptions import W_BaseException, W_Exception, _new_exception
from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault, applevel
from pypy.interpreter.typedef import (
    TypeDef, GetSetProperty, interp_attrproperty_w,
    descr_get_dict, descr_set_dict, descr_del_dict)
from pypy.objspace.std.util import generic_alias_class_getitem

class W_BaseExceptionGroup(W_BaseException):
    """A combination of unrelated exceptions."""

    def __init__(self, space):
        W_BaseException.__init__(self, space)

    @staticmethod
    def descr_new(space, w_subtype, w_message, w_exceptions):
        w_subtype, w_exceptions = space.unpackiterable(check_new_args(space, w_subtype, w_message, w_exceptions), 2)
        exc = space.allocate_instance(W_BaseExceptionGroup, w_subtype)
        W_BaseExceptionGroup.__init__(exc, space)
        exc.w_message = w_message
        exc.w_exceptions = w_exceptions
        exc.args_w = [w_message, w_exceptions]
        return exc

    def descr_init(self, space, args_w):
        if len(args_w) > 0:
            self.w_value = args_w[0]
        W_BaseException.descr_init(self, space, args_w)

    def descr_str(self, space):
        return app_str(space, self)

    def descr_repr(self, space):
        return app_repr(space, self)
    
    def subgroup(self, space, w_condition):
        """
        Returns an exception group that contains only the exceptions from the
        current group that match condition, or None if the result is empty.
        """
        return subgroup(space, self, w_condition)

    def split(self, space, w_condition):
        """
        Like subgroup(), but returns the pair (match, rest) where match is
        subgroup(condition) and rest is the remaining non-matching part.
        """
        return split(space, self, w_condition)


    def derive(self, space, w_excs):
        """
        Returns an exception group that contains only the exceptions from the
        current group that match condition, or None if the result is empty.
        """
        return space.call_function(space.w_BaseExceptionGroup, self.w_message, w_excs)

W_BaseExceptionGroup.typedef = TypeDef(
    'BaseExceptionGroup',
    W_BaseException.typedef,
    __doc__ = W_BaseExceptionGroup.__doc__,
    __module__ = 'builtins',
    __new__ = interp2app(W_BaseExceptionGroup.descr_new),
    __init__ = interp2app(W_BaseExceptionGroup.descr_init),
    __str__ = interp2app(W_BaseExceptionGroup.descr_str),
    __repr__ = interp2app(W_BaseExceptionGroup.descr_repr),
    __class_getitem__ = interp2app(
        generic_alias_class_getitem, as_classmethod=True),
    subgroup = interp2app(W_BaseExceptionGroup.subgroup),
    split = interp2app(W_BaseExceptionGroup.split),
    derive = interp2app(W_BaseExceptionGroup.derive),
    message = interp_attrproperty_w('w_message', W_BaseExceptionGroup),
    exceptions = interp_attrproperty_w('w_exceptions', W_BaseExceptionGroup),
)

class W_ExceptionGroup(W_BaseExceptionGroup):
    pass

W_ExceptionGroup.typedef = TypeDef(
    'ExceptionGroup',
    (W_BaseExceptionGroup.typedef, W_Exception.typedef),
    __module__ = 'builtins',
)
W_ExceptionGroup.typedef.applevel_subclasses_base = W_BaseExceptionGroup

def prep_reraise_star(space, w_obj, w_exc_list):
    return _prep_reraise_star(space, w_obj, w_exc_list)

def collect_eg_leafs(space, w_exc, w_result_set):
    return _collect_eg_leafs(space, w_exc, w_result_set)

def exception_group_projection(space, w_eg, w_keep_list):
    return _exception_group_projection(space, w_eg, w_keep_list)


# lot's of helper code implemented at applevel

import os
appfile = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app_group.py')

with open(appfile, "r") as f:
    content = f.read()

app = applevel(content, filename=__file__)
check_new_args = app.interphook('check_new_args')
app_str = app.interphook('__str__')
app_repr = app.interphook('__repr__')
subgroup = app.interphook('subgroup')
split = app.interphook('split')
_prep_reraise_star = app.interphook('_prep_reraise_star')
_collect_eg_leafs = app.interphook('_collect_eg_leafs')
_exception_group_projection = app.interphook('_exception_group_projection')
