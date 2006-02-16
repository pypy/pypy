"""
The code needed to flow and annotate low-level helpers -- the ll_*() functions
"""

import types
from pypy.tool.sourcetools import valid_identifier
from pypy.annotation import model as annmodel
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

    def default_specialize(pol, funcdesc, args_s):
        if hasattr(funcdesc, 'pyobj') and hasattr(funcdesc.pyobj, 'llresult'):
            # XXX bug mwh to write some tests for this stuff
            funcdesc.overridden = True
            return annmodel.lltype_to_annotation(funcdesc.pyobj.llresult)
        key = []
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
        flowgraph = funcdesc.cachedgraph(tuple(key))
        args_s[:] = new_args_s
        return flowgraph

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
    return annotator.annotate_helper(ll_function, args_s, policy= LowLevelAnnotatorPolicy())

# ___________________________________________________________________
# Mix-level helpers: combining RPython and ll-level

class MixLevelAnnotatorPolicy(LowLevelAnnotatorPolicy):

    def __init__(pol, rtyper):
        pol.rtyper = rtyper

    def default_specialize(pol, funcdesc, args_s):
        name = funcdesc.name
        if name.startswith('ll_') or name.startswith('_ll_'): # xxx can we do better?
            return LowLevelAnnotatorPolicy.default_specialize(pol, funcdesc, args_s)
        else:
            return funcdesc.cachedgraph(None)

    def arglltype(i):
        def specialize_arglltype(pol, funcdesc, args_s):
            key = pol.rtyper.getrepr(args_s[i]).lowleveltype
            alt_name = funcdesc.name+"__for_%sLlT" % key._short_name()
            return funcdesc.cachedgraph(key, alt_name=valid_identifier(alt_name))        
        return specialize_arglltype
        
    specialize__arglltype0 = arglltype(0)
    specialize__arglltype1 = arglltype(1)
    specialize__arglltype2 = arglltype(2)

    del arglltype


def annotate_mixlevel_helper(rtyper, ll_function, args_s):
    pol = MixLevelAnnotatorPolicy(rtyper)
    return rtyper.annotator.annotate_helper(ll_function, args_s, policy=pol)
