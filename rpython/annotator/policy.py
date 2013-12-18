# base annotation policy for specialization
from rpython.annotator.specialize import default_specialize as default
from rpython.annotator.specialize import (
    specialize_argvalue, specialize_argtype, specialize_arglistitemtype,
    specialize_arg_or_var, memo, specialize_call_location)


class AnnotatorPolicy(object):
    """
    Possibly subclass and pass an instance to the annotator to control
    special-casing during annotation
    """

    def event(pol, bookkeeper, what, *args):
        pass

    def get_specializer(pol, directive):
        if directive is None:
            return pol.default_specialize

        # specialize[(args)]
        directive_parts = directive.split('(', 1)
        if len(directive_parts) == 1:
            [name] = directive_parts
            parms = ()
        else:
            name, parms = directive_parts
            try:
                parms = eval("(lambda *parms: parms)(%s" % parms)
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                raise Exception, "broken specialize directive parms: %s" % directive
        name = name.replace(':', '__')
        try:
            specializer = getattr(pol, name)
        except AttributeError:
            raise AttributeError("%r specialize tag not defined in annotation"
                                 "policy %s" % (name, pol))
        else:
            if not parms:
                return specializer
            else:
                def specialize_with_parms(funcdesc, args_s):
                    return specializer(funcdesc, args_s, *parms)
                return specialize_with_parms

    # common specializations

    default_specialize = staticmethod(default)
    specialize__memo = staticmethod(memo)
    specialize__arg = staticmethod(specialize_argvalue) # specialize:arg(N)
    specialize__arg_or_var = staticmethod(specialize_arg_or_var)
    specialize__argtype = staticmethod(specialize_argtype) # specialize:argtype(N)
    specialize__arglistitemtype = staticmethod(specialize_arglistitemtype)
    specialize__call_location = staticmethod(specialize_call_location)

    def specialize__ll(pol, *args):
        from rpython.rtyper.annlowlevel import LowLevelAnnotatorPolicy
        return LowLevelAnnotatorPolicy.default_specialize(*args)

    def specialize__ll_and_arg(pol, *args):
        from rpython.rtyper.annlowlevel import LowLevelAnnotatorPolicy
        return LowLevelAnnotatorPolicy.specialize__ll_and_arg(*args)

    def no_more_blocks_to_annotate(pol, annotator):
        # hint to all pending specializers that we are done
        for callback in annotator.bookkeeper.pending_specializations:
            callback()
        del annotator.bookkeeper.pending_specializations[:]
