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
    oldblocks = annotator.annotated.keys()
    s = annotator.build_types(ll_function, args_s)
    newblocks = [block for block in annotator.annotated.iterkeys() if block not in oldblocks]
    # invoke annotation simplifcations for the new blocks
    annotator.simplify(block_subset=newblocks)
##    finally:
##        annotator.policy = saved
    return s
