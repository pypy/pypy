from pypy.translator.goal.ann_override import PyPyAnnotatorPolicy

class CPyAnnotatorPolicy(PyPyAnnotatorPolicy):
    allow_someobjects = True
    
    # XXX make it more subtle: only allow SomeObjects in
    # some specific functions, not all of them.
    # Currently only trampoline() in wrapper.py should need them.
