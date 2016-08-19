import weakref

import py

from rpython.rlib import rgc, debug
from rpython.rlib.objectmodel import (keepalive_until_here, compute_unique_id,
    compute_hash, current_object_addr_as_int)
from rpython.rtyper.lltypesystem import lltype, llmemory
from rpython.rtyper.lltypesystem.lloperation import llop
from rpython.rtyper.lltypesystem.rstr import STR
from rpython.translator.c.test.test_genc import compile


def setup_module(mod):
    from rpython.rtyper.tool.rffi_platform import configure_qcgc
    from rpython.translator.platform import CompilationError
    configure_qcgc()


class AbstractGCTestClass(object):
    gcpolicy = "qcgc"
    use_threads = False
    extra_options = {}

    # deal with cleanups
    def setup_method(self, meth):
        self._cleanups = []

    def teardown_method(self, meth):
        while self._cleanups:
            #print "CLEANUP"
            self._cleanups.pop()()

    def getcompiled(self, func, argstypelist=[], annotatorpolicy=None,
                    extra_options={}):
        return compile(func, argstypelist, gcpolicy=self.gcpolicy,
                       thread=self.use_threads, **extra_options)


class TestUsingBoehm(AbstractGCTestClass):
    gcpolicy = "boehm"

    def test_malloc_a_lot(self):
        def malloc_a_lot():
            i = 0
            while i < 10:
                i += 1
                a = [1] * 10
                j = 0
                while j < 20:
                    j += 1
                    a.append(j)
        fn = self.getcompiled(malloc_a_lot)
        fn()
