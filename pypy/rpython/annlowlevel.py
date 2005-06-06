"""
The code needed to flow and annotate low-level helpers -- the ll_*() functions
"""

##from pypy.translator.annrpython import BasicAnnotatorPolicy


##class LowLevelAnnotatorPolicy(BasicAnnotatorPolicy):

##    def compute_at_fixpoint(self, annotator):
##        pass


def annotate_lowlevel_helper(annotator, ll_function, args_s):
##    saved = annotator.policy
##    annotator.policy = LowLevelAnnotatorPolicy()
##    try:
    annotator.build_types(ll_function, args_s)
##    finally:
##        annotator.policy = saved
