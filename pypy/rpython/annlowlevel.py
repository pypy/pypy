"""
The code needed to flow and annotate low-level helpers -- the ll_*() functions
"""

import types
from pypy.annotation import model as annmodel
from pypy.annotation.specialize import decide_callable
from pypy.annotation.policy import AnnotatorPolicy
from pypy.rpython.lltypesystem import lltype
from pypy.rpython import extfunctable

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
        val = self.val
        if isinstance(val, lltype.LowLevelType):
            return val._short_name() + 'LlT'
        s = getattr(val, '__name__', None)
        if s is None:
            compact = getattr(val, 'compact_repr', None)
            if compact is None:
                s = repr(val)
            else:
                s = compact()        
        return s + 'Const'

class LowLevelAnnotatorPolicy(AnnotatorPolicy):
    allow_someobjects = False

    def default_specialize(pol, bookkeeper, ignored, spaceop, func, args, mono):
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
                try:
                    key.append(annmodel.annotation_to_lltype(s_obj))
                except ValueError:
                    # passing non-low-level types to a ll_* function is allowed
                    # for module/ll_*
                    key.append(s_obj.__class__)
        return tuple(key), bookkeeper.build_args('simple_call', new_args_s)

    def override__init_opaque_object(pol, s_opaqueptr, s_value):
        assert isinstance(s_opaqueptr, annmodel.SomePtr)
        assert isinstance(s_opaqueptr.ll_ptrtype.TO, lltype.OpaqueType)
        assert isinstance(s_value, annmodel.SomeExternalObject)
        exttypeinfo = extfunctable.typetable[s_value.knowntype]
        assert s_opaqueptr.ll_ptrtype.TO._exttypeinfo == exttypeinfo
        return annmodel.SomeExternalObject(exttypeinfo.typ)

    def override__from_opaque_object(pol, s_opaqueptr):
        assert isinstance(s_opaqueptr, annmodel.SomePtr)
        assert isinstance(s_opaqueptr.ll_ptrtype.TO, lltype.OpaqueType)
        exttypeinfo = s_opaqueptr.ll_ptrtype.TO._exttypeinfo
        return annmodel.SomeExternalObject(exttypeinfo.typ)

    def override__to_opaque_object(pol, s_value):
        assert isinstance(s_value, annmodel.SomeExternalObject)
        exttypeinfo = extfunctable.typetable[s_value.knowntype]
        return annmodel.SomePtr(lltype.Ptr(exttypeinfo.get_lltype()))


def annotate_lowlevel_helper(annotator, ll_function, args_s):
    saved = annotator.policy, annotator.added_blocks
    annotator.policy = LowLevelAnnotatorPolicy()
    try:
        args = annotator.bookkeeper.build_args('simple_call', args_s)
        (ll_function, args), key = decide_callable(annotator.bookkeeper, None, ll_function, args, mono=True, unpacked=True)
        args_s, kwds_s = args.unpack()
        assert not kwds_s
        annotator.added_blocks = {}
        s = annotator.build_types(ll_function, args_s)
        # invoke annotation simplifications for the new blocks
        annotator.simplify(block_subset=annotator.added_blocks)
    finally:
        annotator.policy, annotator.added_blocks = saved
    return s, ll_function
