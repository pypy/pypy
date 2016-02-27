from rpython.jit.backend.llsupport.gcstress.test.zrpy_gc_hypo_test import GCHypothesis


class TestGCHypothesis(GCHypothesis):
    # runs ../../llsupport/gcstress/test/zrpy_gc_hypo_test.py
    gcrootfinder = "shadowstack"
    gc = "incminimark"
