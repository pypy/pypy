# base annotation policy for overrides and specialization
from pypy.annotation.specialize import memo, ctr_location, default_specialize as default

class AnnotatorPolicy:
    """
    Possibly subclass and pass an instance to the annotator to control special casing during annotation
    """

    def getspecialcase(pol, kind, obj):
        if hasattr(obj, '_annspecialcase_'):
            sc = obj._annspecialcase_.split(':')
            assert len(sc) ==2, "_annspecialcase_ should have the form kind:tag"
            if sc[0] == kind:
                return sc[1]
            assert sc[0] in ('override', 'specialize'), "_annspecialcase_ kinds are only 'override', 'specialize'"
        return None

    def override(pol, func, inputcells):
        tag = pol.getspecialcase('override', func)
        if tag is None:
            return None
        try:
            override = getattr(pol, 'override__%s' % tag)
        except AttributeError:
            raise AttributeError, "%s override tag found in user program but not defined in annotation policy %s" % (tag, pol) 

        return override(*inputcells)

    def specialize(pol, bookkeeper, spaceop, func, args, mono):
        tag = pol.getspecialcase('specialize', func)
        if tag is None:
            return pol.default_specialize(bookkeeper, spaceop, func, args, mono)
        
        try:
            specialize = getattr(pol, 'specialize__%s' % tag)
        except AttributeError:
            raise AttributeError, "%s specialize tag found in user program but not defined in annotation policy %s" % (tag, pol) 

        return specialize(bookkeeper, spaceop, func, args, mono)
        
        
    # common specializations

    default_specialize = staticmethod(default)
    specialize__memo = staticmethod(memo)
    specialize__ctr_location = staticmethod(ctr_location)
