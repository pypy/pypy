# base annotation policy for specialization
from pypy.annotation.specialize import default_specialize as default
from pypy.annotation.specialize import specialize_argvalue, specialize_argtype, specialize_arglistitemtype, specialize_arg_or_var
from pypy.annotation.specialize import memo, specialize_call_location
# for some reason, model must be imported first,
# or we create a cycle.
from pypy.annotation import model as annmodel
from pypy.annotation.bookkeeper import getbookkeeper
from pypy.annotation.signature import Sig


class BasicAnnotatorPolicy(object):
    allow_someobjects = True

    def event(pol, bookkeeper, what, *args):
        pass

    def get_specializer(pol, tag):
        return pol.no_specialization

    def no_specialization(pol, funcdesc, args_s):
        return funcdesc.cachedgraph(None)

    def no_more_blocks_to_annotate(pol, annotator):
        # hint to all pending specializers that we are done
        for callback in annotator.bookkeeper.pending_specializations:
            callback()
        del annotator.bookkeeper.pending_specializations[:]

    def _adjust_space_config(self, space):
        # allow to override space options.
        if getattr(self, 'do_imports_immediately', None) is not None:
            space.do_imports_immediately = self.do_imports_immediately

class AnnotatorPolicy(BasicAnnotatorPolicy):
    """
    Possibly subclass and pass an instance to the annotator to control special casing during annotation
    """

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
        from pypy.rpython.annlowlevel import LowLevelAnnotatorPolicy
        return LowLevelAnnotatorPolicy.default_specialize(*args)

    def specialize__ll_and_arg(pol, *args):
        from pypy.rpython.annlowlevel import LowLevelAnnotatorPolicy
        return LowLevelAnnotatorPolicy.specialize__ll_and_arg(*args)

class StrictAnnotatorPolicy(AnnotatorPolicy):
    allow_someobjects = False
