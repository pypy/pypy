"""
The code needed to flow and annotate low-level helpers -- the ll_*() functions
"""

import types
from pypy.annotation import model as annmodel
from pypy.annotation.specialize import decide_callable
from pypy.annotation.policy import BasicAnnotatorPolicy

def not_const(s_obj): # xxx move it somewhere else
    if s_obj.is_constant():
        new_s_obj = annmodel.SomeObject()
        new_s_obj.__class__ = s_obj.__class__
        new_s_obj.__dict__ = s_obj.__dict__
        del new_s_obj.const
        s_obj = new_s_obj
    return s_obj


class KeyComp(object):
    def __init__(self, val):
        self.val = val
    def __eq__(self, other):
        return self.__class__ == other.__class__ and self.val == other.val
    def __ne__(self, other):
        return not (self == other)
    def __hash__(self):
        return hash(self.val)
    def __str__(self):
        return getattr(self.val, '__name__', repr(self.val)) + 'Const'

class LowLevelAnnotatorPolicy(BasicAnnotatorPolicy):

    def specialize(pol, bookkeeper, spaceop, func, args, mono):
        args_s, kwds_s = args.unpack()
        assert not kwds_s
        if not args_s or not isinstance(func, types.FunctionType):
            return None, None
        key = [func]
        new_args_s = []
        for s_obj in args_s:
            if isinstance(s_obj, annmodel.SomePBC):
                assert s_obj.is_constant(), "ambiguous low-level helper specialization"
                key.append(KeyComp(s_obj.const))
                new_args_s.append(s_obj)
            else:
                new_args_s.append(not_const(s_obj))
                key.append(annmodel.annotation_to_lltype(s_obj))
        return tuple(key), bookkeeper.build_args('simple_call', new_args_s)
        

def annotate_lowlevel_helper(annotator, ll_function, args_s):
    saved = annotator.policy
    annotator.policy = LowLevelAnnotatorPolicy()
    try:
        args = annotator.bookkeeper.build_args('simple_call', args_s)
        (ll_function, args), key = decide_callable(annotator.bookkeeper, None, ll_function, args, mono=True, unpacked=True)
        args_s, kwds_s = args.unpack()
        assert not kwds_s
        oldblocks = annotator.annotated.copy()
        s = annotator.build_types(ll_function, args_s)
        newblocks = [block for block in annotator.annotated.iterkeys() if block not in oldblocks]
        # invoke annotation simplifications for the new blocks
        annotator.simplify(block_subset=newblocks)
    finally:
        annotator.policy = saved
    return s, ll_function
