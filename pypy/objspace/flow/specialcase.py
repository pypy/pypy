import types
from pypy.interpreter import pyframe, baseobjspace
from pypy.interpreter.error import OperationError
from pypy.objspace.flow.objspace import UnwrapException
from pypy.objspace.flow.model import Constant


def getconstclass(space, w_cls):
    try:
        ecls = space.unwrap(w_cls)
    except UnwrapException:
        pass
    else:
        if isinstance(ecls, (type, types.ClassType)):
            return ecls
    return None


def normalize_exception(space, args):
    """Special-case for 'raise' statements.

    Only accept the following syntaxes:
    * raise Class
    * raise Class, Arg
    * raise Class(...)
    """
    assert len(args.args_w) == 2 and args.kwds_w == {}
    w_arg1, w_arg2 = args.args_w
    etype = getconstclass(space, w_arg1)
    if etype is not None:
        # raise Class or raise Class, Arg: no normalization
        return (w_arg1, w_arg2)
    else:
        # raise Instance: we need a hack to figure out of which class it is.
        # Normally, Instance should have been created by the previous operation
        # which should be a simple_call(<Class>, ...).
        # Fetch the <Class> out of there.  (This doesn't work while replaying)
        spaceop = space.executioncontext.crnt_ops[-1]
        assert spaceop.opname == 'simple_call'
        assert spaceop.result is w_arg1
        w_type = spaceop.args[0]
        return (w_type, w_arg2)
    # this function returns a real tuple that can be handled
    # by FlowObjSpace.unpacktuple()

def loadfromcache(space, args):
    # XXX need some way to know how to fully initialize the cache
    print space, args
    assert len(args.args_w) == 2 and args.kwds_w == {}
    w_key, w_builder = args.args_w
    w_cache = Constant('space_cache')   # temporary
    return space.do_operation('getitem', w_cache, w_key)


def import_(space, args):
    assert len(args.args_w) == 4 and args.kwds_w == {}
    unwrapped_args = []
    for w_arg in args.args_w:
        assert isinstance(w_arg, Constant)
        unwrapped_args.append(space.unwrap(w_arg))
    return space.wrap(__import__(*unwrapped_args))

def setup(space):
    fn = pyframe.normalize_exception.get_function(space)
    space.specialcases[fn] = normalize_exception
    fn = baseobjspace.ObjSpace.loadfromcache.im_func
    space.specialcases[fn] = loadfromcache
    space.specialcases[__import__] = import_
