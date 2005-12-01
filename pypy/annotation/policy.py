# base annotation policy for overrides and specialization
from pypy.annotation.specialize import default_specialize as default
from pypy.annotation.specialize import argtype, argvalue
from pypy.annotation.specialize import memo, methodmemo
# for some reason, model must be imported first,
# or we create a cycle.
from pypy.annotation import model as annmodel
from pypy.annotation.bookkeeper import getbookkeeper


class BasicAnnotatorPolicy:
    allow_someobjects = True

    def event(pol, bookkeeper, what, *args):
        pass

    def get_specializer(pol, tag):
        return pol.no_specialization

    def no_specialization(pol, funcdesc, args_s):
        return funcdesc.cachedgraph(None)

    def compute_at_fixpoint(pol, annotator):
        annotator.bookkeeper.compute_at_fixpoint()


class AnnotatorPolicy(BasicAnnotatorPolicy):
    """
    Possibly subclass and pass an instance to the annotator to control special casing during annotation
    """

    def get_specializer(pol, directive):
        if directive is None:
            return pol.default_specialize

        name = directive.replace(':', '__')
        try:
            specializer = getattr(pol, name)
        except AttributeError:
            raise AttributeError("%r specialize tag not defined in annotation"
                                 "policy %s" % (directive, pol))
        if directive.startswith('override:'):
            # different signature: override__xyz(*args_s)
            def specialize_override(funcdesc, args_s):
                funcdesc.overridden = True
                return specializer(*args_s)
            return specialize_override
        else:
            return specializer
        
    # common specializations

    default_specialize = staticmethod(default)
    specialize__memo = staticmethod(memo)
    specialize__methodmemo = staticmethod(methodmemo)
    specialize__arg0 = staticmethod(argvalue(0))
    specialize__argtype0 = staticmethod(argtype(0))
    specialize__arg1 = staticmethod(argvalue(1))
    specialize__argtype1 = staticmethod(argtype(1))
    specialize__arg2 = staticmethod(argvalue(2))
    specialize__argtype2 = staticmethod(argtype(2))
    specialize__arg3 = staticmethod(argvalue(3))
    specialize__argtype3 = staticmethod(argtype(3))
    specialize__arg4 = staticmethod(argvalue(4))
    specialize__argtype4 = staticmethod(argtype(4))
    specialize__arg5 = staticmethod(argvalue(5))
    specialize__argtype5 = staticmethod(argtype(5))

    def override__ignore(pol, *args):
        bk = getbookkeeper()
        return bk.immutablevalue(None)
