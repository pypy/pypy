from rpython.jit.backend.x86.test.test_basic import Jit386Mixin
from rpython.jit.metainterp.test.test_strstorage import TestStrStorage as _TestStrStorage


class TestStrStorage(Jit386Mixin, _TestStrStorage):
    # for the individual tests see
    # ====> ../../../metainterp/test/test_strstorage.py
    pass
