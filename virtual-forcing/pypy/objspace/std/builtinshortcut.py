from pypy.interpreter.baseobjspace import ObjSpace
from pypy.interpreter.error import OperationError
from pypy.objspace.descroperation import DescrOperation
from pypy.objspace.std.multimethod import FailedToImplement
from pypy.objspace.std.boolobject import W_BoolObject
from pypy.tool.sourcetools import func_with_new_name

# ____________________________________________________________
#
#  The sole purpose of this file is performance.
#  It speeds up the dispatch of operations between
#  built-in objects.
#

# this is a selection... a few operations are missing because they are
# thought to be very rare or most commonly used with non-builtin types
METHODS_WITH_SHORTCUT = dict.fromkeys(
    ['add', 'sub', 'mul', 'truediv', 'floordiv', 'div',
     'mod', 'lshift', 'rshift', 'and_', 'or_', 'xor', 'pow',
     'lt', 'le', 'eq', 'ne', 'gt', 'ge', 'contains',
     # unary
     'len', 'nonzero', 'repr', 'str', 'hash',
     'neg', 'invert', 'index', 'iter', 'next', 'buffer',
     'getitem', 'setitem', 'int',
     # in-place
     'inplace_add', 'inplace_sub', 'inplace_mul', 'inplace_truediv',
     'inplace_floordiv', 'inplace_div', 'inplace_mod', 'inplace_pow',
     'inplace_lshift', 'inplace_rshift', 'inplace_and', 'inplace_or',
     'inplace_xor',
 ])

KNOWN_MISSING = ['getattr',   # mostly non-builtins or optimized by CALL_METHOD
                 'setattr', 'delattr', 'userdel',  # mostly for non-builtins
                 'get', 'set', 'delete',   # uncommon (except on functions)
                 'getslice', 'setslice', 'delslice',  # see below
                 'delitem',                       # rare stuff?
                 'abs', 'hex', 'oct',             # rare stuff?
                 'pos', 'divmod', 'cmp',          # rare stuff?
                 'float', 'long', 'coerce',       # rare stuff?
                 ]
# We cannot support {get,set,del}slice right now because
# DescrOperation.{get,set,del}slice do a bit more work than just call
# the special methods: they call old_slice_range().  See e.g.
# test_builtinshortcut.AppTestString.

for _name, _, _, _specialmethods in ObjSpace.MethodTable:
    if _specialmethods:
        assert _name in METHODS_WITH_SHORTCUT or _name in KNOWN_MISSING, (
            "operation %r should be in METHODS_WITH_SHORTCUT or KNOWN_MISSING"
            % (_name,))


def filter_out_conversions(typeorder):
    res = {}
    for cls, order in typeorder.iteritems():        
        res[cls] = [(target_type, converter) for (target_type, converter) in
                                                 order if converter is None]
    return res


def install(space, mm, fallback_mm=None):
    """Install a function <name>() on the space instance which invokes
    a shortcut for built-in types.  Returns the shortcutting multimethod
    object or None.
    """
    name = mm.name
    if name not in METHODS_WITH_SHORTCUT:
        return None

    # can be called multiple times without re-installing
    if name in space.__dict__:
        mm1, shortcut_method = space.__dict__[name].builtinshortcut
        assert mm1 is mm
        return shortcut_method

    #print 'installing shortcut for:', name
    assert hasattr(DescrOperation, name)

    base_method = getattr(space.__class__, name)

    # Basic idea: we first try to dispatch the operation using purely
    # the multimethod.  If this is done naively, subclassing a built-in
    # type like 'int' and overriding a special method like '__add__'
    # doesn't work any more, because the multimethod will accept the int
    # subclass and compute the result in the built-in way.  To avoid
    # this issue, we tweak the shortcut multimethods so that these ones
    # (and only these ones) never match the interp-level subclasses
    # built in pypy.interpreter.typedef.get_unique_interplevel_subclass.
    expanded_order = space.model.get_typeorder_with_empty_usersubcls()
    if fallback_mm:
        mm = mm.merge_with(fallback_mm)
    shortcut_method = mm.install_not_sliced(filter_out_conversions(expanded_order))

    def operate(*args_w):
        try:
            return shortcut_method(space, *args_w)
        except FailedToImplement:
            pass
        return base_method(space, *args_w)

    operate = func_with_new_name(operate, name)
    operate.builtinshortcut = (mm, shortcut_method)
    setattr(space, name, operate)
    return shortcut_method


def install_is_true(space, mm_nonzero, mm_len):
    shortcut = install(space, mm_nonzero, fallback_mm = mm_len)
    assert 'is_true' not in space.__dict__

    def is_true(w_obj):
        # a bit of duplication of the logic from DescrOperation.is_true...
        try:
            w_res = shortcut(space, w_obj)
        except FailedToImplement:
            pass
        else:
            # the __nonzero__ method of built-in objects should
            # always directly return a Bool; however, the __len__ method
            # of built-in objects typically returns an unwrappable integer
            if isinstance(w_res, W_BoolObject):
                return w_res.boolval
            try:
                return space.int_w(w_res) != 0
            except OperationError:
                # I think no OperationError other than w_OverflowError
                # could occur here
                w_obj = w_res

        # general case fallback
        return DescrOperation.is_true(space, w_obj)

    space.is_true = is_true
