from pypy.translator.goal.ann_override import PyPyAnnotatorPolicy

class CPyAnnotatorPolicy(PyPyAnnotatorPolicy):
    """Annotation policy to compile CPython extension modules with
    the CPyObjSpace.
    """
