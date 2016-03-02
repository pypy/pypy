from rpython.jit.backend.llsupport.tl.test.zrpy_gc_hypo_test import GCHypothesis

import py

py.test.skip("not yet working")

class TestGCHypothesis(GCHypothesis):
    # runs ../../llsupport/tl/test/zrpy_gc_hypo_test.py
    gcrootfinder = "shadowstack"
    gc = "incminimark"
