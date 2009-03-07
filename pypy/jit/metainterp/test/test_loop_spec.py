import py
from pypy.jit.metainterp.test import test_loop


class TestLoopSpec(test_loop.TestLoop):
    specialize = True

    # ====> test_loop.py
