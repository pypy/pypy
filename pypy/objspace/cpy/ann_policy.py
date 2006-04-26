from pypy.translator.goal.ann_override import PyPyAnnotatorPolicy
from pypy.annotation.pairtype import pair

class CPyAnnotatorPolicy(PyPyAnnotatorPolicy):
    """Annotation policy to compile CPython extension modules with
    the CPyObjSpace.
    """

    def __init__(self, space):
        PyPyAnnotatorPolicy.__init__(self, single_space=space)
        self.spaces = {}

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
            for obj, w_obj in pending.items():
                pair(space, obj).follow_annotations(annotator.bookkeeper,
                                                    w_obj)
            # restart this loop: for all we know follow_annotations()
            # could have found new objects
