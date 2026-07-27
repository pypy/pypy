import sys
import py
from rpython.rtyper.tool.rffi_platform import CompilationError


class BaseAppTest:
    spaceconfig = dict(usemodules=['_continuation'], continuation=True)

    def setup_class(cls):
        if '__pypy__' in sys.builtin_module_names:
            # matches the check in rstacklet._getgcrootfinder(): every
            # test here ends up calling stacklet_switch() untranslated,
            # which is unsafe on top of a translated pypy's own C stack.
            # Skip the whole class upfront instead of hitting this
            # mid-test in each one individually.
            py.test.skip("cannot run the stacklet tests on top of pypy: "
                         "calling directly the C function stacklet_switch() "
                         "will crash, depending on details of your config")
        try:
            import rpython.rlib.rstacklet
        except CompilationError as e:
            py.test.skip("cannot import rstacklet: %s" % e)
