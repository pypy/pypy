from pypy.translator.goal.ann_override import PyPyAnnotatorPolicy
from pypy.annotation import model as annmodel
from pypy.interpreter.error import OperationError
from pypy.objspace.cpy.ctypes_base import W_Object, rctypes_pyerrchecker

class CPyAnnotatorPolicy(PyPyAnnotatorPolicy):
    """Annotation policy to compile CPython extension modules with
    the CPyObjSpace.
    """

    def __init__(self, space):
        PyPyAnnotatorPolicy.__init__(self, single_space=space)

    def no_more_blocks_to_annotate(self, annotator):
        PyPyAnnotatorPolicy.no_more_blocks_to_annotate(self, annotator)

        # annotate all indirectly reachable call-back functions
        space = self.single_space
        pending = {}
        while True:
            nb_done = len(pending)
            pending.update(space.wrap_cache)
            if len(pending) == nb_done:
                break
            for w_obj, obj, follow in pending.values():
                follow(annotator.bookkeeper, w_obj)
            # restart this loop: for all we know follow_annotations()
            # could have found new objects

        # force w_type/w_value/w_traceback attrs into the OperationError class
        bk = annotator.bookkeeper
        classdef = bk.getuniqueclassdef(OperationError)
        s_instance = annmodel.SomeInstance(classdef=classdef)
        for name in ['w_type', 'w_value', 'w_traceback']:
            s_instance.setattr(bk.immutablevalue(name),
                               bk.valueoftype(W_Object))

        # annotate rctypes_pyerrchecker()
        uniquekey = rctypes_pyerrchecker
        s_pyerrchecker = bk.immutablevalue(rctypes_pyerrchecker)
        s_result = bk.emulate_pbc_call(uniquekey, s_pyerrchecker, [])
        assert annmodel.s_None.contains(s_result)

    def specialize__all_someobjects(self, funcdesc, args_s):
        return funcdesc.cachedgraph(None)
