"""Implements the core parts of flow graph creation, in tandem
with rpython.flowspace.flowcontext.
"""

import __builtin__
from inspect import CO_NEWLOCALS

from rpython.flowspace.argument import CallSpec
from rpython.flowspace.model import Constant, Variable, checkgraph, const
from rpython.flowspace.bytecode import HostCode
from rpython.flowspace.operation import op
from rpython.flowspace.flowcontext import (FlowSpaceFrame, fixeggblocks,
    FlowingError, Raise)
from rpython.flowspace.generator import (tweak_generator_graph,
        bootstrap_generator)
from rpython.flowspace.pygraph import PyGraph
from rpython.flowspace.specialcase import SPECIAL_CASES


def _assert_rpythonic(func):
    """Raise ValueError if ``func`` is obviously not RPython"""
    if func.func_doc and func.func_doc.lstrip().startswith('NOT_RPYTHON'):
        raise ValueError("%r is tagged as NOT_RPYTHON" % (func,))
    if func.func_code.co_cellvars:
        raise ValueError("RPython functions cannot create closures")
    if not (func.func_code.co_flags & CO_NEWLOCALS):
        raise ValueError("The code object for a RPython function should have "
                "the flag CO_NEWLOCALS set.")


# ______________________________________________________________________
class FlowObjSpace(object):
    """NOT_RPYTHON.
    The flow objspace space is used to produce a flow graph by recording
    the space operations that the interpreter generates when it interprets
    (the bytecode of) some function.
    """
    def build_flow(self, func):
        return build_flow(func, self)

    def call_method(self, w_obj, methname, *arg_w):
        w_meth = op.getattr(w_obj, const(methname)).eval(self.frame)
        return self.call_function(w_meth, *arg_w)

    def call_function(self, w_func, *args_w):
        args = CallSpec(list(args_w))
        return self.call(w_func, args)

    def appcall(self, func, *args_w):
        """Call an app-level RPython function directly"""
        w_func = const(func)
        return op.simple_call(w_func, *args_w).eval(self.frame)

    def call(self, w_callable, args):
        if isinstance(w_callable, Constant):
            fn = w_callable.value
            if hasattr(fn, "_flowspace_rewrite_directly_as_"):
                fn = fn._flowspace_rewrite_directly_as_
                w_callable = const(fn)
            try:
                sc = SPECIAL_CASES[fn]   # TypeError if 'fn' not hashable
            except (KeyError, TypeError):
                pass
            else:
                if args.keywords:
                    raise FlowingError(
                        "should not call %r with keyword arguments" % (fn,))
                return sc(self, *args.as_list())

        if args.keywords or isinstance(args.w_stararg, Variable):
            shape, args_w = args.flatten()
            hlop = op.call_args(w_callable, Constant(shape), *args_w)
        else:
            hlop = op.simple_call(w_callable, *args.as_list())
        return self.frame.do_op(hlop)

    def find_global(self, w_globals, varname):
        try:
            value = w_globals.value[varname]
        except KeyError:
            # not in the globals, now look in the built-ins
            try:
                value = getattr(__builtin__, varname)
            except AttributeError:
                raise FlowingError("global name '%s' is not defined" % varname)
        return const(value)


def build_flow(func, space=FlowObjSpace()):
    """
    Create the flow graph for the function.
    """
    _assert_rpythonic(func)
    code = HostCode._from_code(func.func_code)
    if (code.is_generator and
            not hasattr(func, '_generator_next_method_of_')):
        graph = PyGraph(func, code)
        block = graph.startblock
        for name, w_value in zip(code.co_varnames, block.framestate.mergeable):
            if isinstance(w_value, Variable):
                w_value.rename(name)
        return bootstrap_generator(graph)
    graph = PyGraph(func, code)
    frame = space.frame = FlowSpaceFrame(space, graph, code)
    frame.build_flow()
    fixeggblocks(graph)
    checkgraph(graph)
    if code.is_generator:
        tweak_generator_graph(graph)
    return graph
