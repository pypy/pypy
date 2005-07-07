# base annotation policy for overrides and specialization
from pypy.annotation.specialize import memo, ctr_location, default_specialize as default
from pypy.annotation.specialize import argtype, argvalue
# for some reason, model must be imported first,
# or we create a cycle.
from pypy.annotation import model as annmodel
from pypy.annotation.bookkeeper import getbookkeeper


class BasicAnnotatorPolicy:
    
    def specialize(pol, bookkeeper, spaceop, func, args, mono):
        return None, None

    def compute_at_fixpoint(pol, annotator):
        annotator.bookkeeper.compute_at_fixpoint()


class AnnotatorPolicy(BasicAnnotatorPolicy):
    """
    Possibly subclass and pass an instance to the annotator to control special casing during annotation
    """

    def specialize(pol, bookkeeper, spaceop, func, args, mono):
        if hasattr(func, '_annspecialcase_'):
            directive = func._annspecialcase_
            if directive.startswith('specialize:'):
                directive = directive[len('specialize:'):]
            tag_mod = directive.split(':', 1)
            if len(tag_mod) == 1:
                tag, = tag_mod
                mod = None
            else:
                tag, mod = tag_mod
        else:
            return pol.default_specialize(bookkeeper, None, spaceop, func, args, mono)
        
        try:
            specialize = getattr(pol, 'specialize__%s' % tag)
        except AttributeError:
            raise AttributeError("%s specialize tag found in callable %r "
                                 "(file %s:%d) but not defined in annotation "
                                 "policy %s" % (tag, func.func_name,
                                                func.func_code.co_filename,
                                                func.func_code.co_firstlineno,
                                                pol))

        return specialize(bookkeeper, mod, spaceop, func, args, mono)

    def specialize__override(pol, bookkeeper, mod, spaceop, func, args, mono):
        from pypy.annotation.model import SomeObject
        override_tag = mod

        try:
            override = getattr(pol, 'override__%s' % override_tag)
        except AttributeError:
            raise AttributeError("'override:%s' found in callable %r "
                                 "(file %s:%d) but not defined in annotation "
                                 "policy %s" % (override_tag, func.func_name,
                                                func.func_code.co_filename,
                                                func.func_code.co_firstlineno ,
                                                pol))

        inputcells = bookkeeper.get_inputcells(func, args)
        r = override(*inputcells)

        assert isinstance(r, SomeObject)
        return r, None
        
    # common specializations

    default_specialize = staticmethod(default)
    specialize__memo = staticmethod(memo)
    specialize__ctr_location = staticmethod(ctr_location)
    specialize__arg0 = staticmethod(argvalue(0))
    specialize__argtype0 = staticmethod(argtype(0))
    specialize__arg1 = staticmethod(argvalue(1))
    specialize__argtype1 = staticmethod(argtype(1))

    def override__ignore(pol, *args):
        bk = getbookkeeper()
        return bk.immutablevalue(None)
