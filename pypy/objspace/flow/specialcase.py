import types
from pypy.interpreter import pyopcode
from pypy.interpreter.error import OperationError
from pypy.objspace.flow.objspace import UnwrapException
from pypy.objspace.flow.model import Variable


def getconstclass(space, w_cls):
    try:
        ecls = space.unwrap(w_cls)
    except UnwrapException:
        pass
    else:
        if isinstance(ecls, (type, types.ClassType)):
            return ecls
    return None


def prepare_raise(space, args):
    """Special-case for 'raise' statements.

    Only accept the following syntaxes:
    * raise Class
    * raise Class, Arg
    * raise Class(...)
    """
    assert len(args.args_w) == 2 and args.kwds_w == {}
    w_arg1, w_arg2 = args.args_w
    #
    # Note that we immediately raise the correct OperationError to
    # prevent further processing by pyopcode.py.
    #
    etype = getconstclass(space, w_arg1)
    if etype is not None:
        # raise Class or raise Class, Arg: ignore the Arg
        raise OperationError(w_arg1, Variable())
    else:
        # raise Instance: we need a hack to figure out of which class it is.
        # Normally, Instance should have been created by the previous operation
        # which should be a simple_call(<Class>, ...).
        # Fetch the <Class> out of there.  (This doesn't work while replaying)
        spaceop = space.executioncontext.crnt_ops[-1]
        assert spaceop.opname == 'simple_call'
        assert spaceop.result is w_arg1
        w_type = spaceop.args[0]
        raise OperationError(w_type, w_arg2)


def setup(space):
    return {
        pyopcode.prepare_raise.get_function(space): prepare_raise,
        }
