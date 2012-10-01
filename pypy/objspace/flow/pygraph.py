"""
Implements flow graphs for Python callables
"""
from pypy.objspace.flow.model import (FunctionGraph, Constant, Variable,
        SpaceOperation)
from pypy.objspace.flow.framestate import FrameState

class PyGraph(FunctionGraph):
    """
    Flow graph for a Python function
    """

    def __init__(self, func, code):
        from pypy.objspace.flow.flowcontext import SpamBlock
        data = [None] * code.co_nlocals
        for i in range(code.getformalargcount()):
            data[i] = Variable()
        state = FrameState(data + [Constant(None), Constant(None)], [], 0)
        initialblock = SpamBlock(state)
        if code.is_generator:
            initialblock.operations.append(
                SpaceOperation('generator_mark', [], Variable()))

        super(PyGraph, self).__init__(self._sanitize_funcname(func), initialblock)
        self.func = func
        self.signature = code.signature()
        self.defaults = func.func_defaults or ()
        self.is_generator = code.is_generator

    @staticmethod
    def _sanitize_funcname(func):
        # CallableFactory.pycall may add class_ to functions that are methods
        name = func.func_name
        class_ = getattr(func, 'class_', None)
        if class_ is not None:
            name = '%s.%s' % (class_.__name__, name)
        for c in "<>&!":
            name = name.replace(c, '_')

