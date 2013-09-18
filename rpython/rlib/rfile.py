
""" This file makes open() and friends RPython
"""

import os
from rpython.annotator.model import SomeObject, SomeString, SomeInteger
from rpython.rtyper.extregistry import ExtRegistryEntry
from rpython.rtyper.extfunc import register_external

class SomeFile(SomeObject):
    def method_write(self, s_arg):
        assert isinstance(s_arg, SomeString)

    def method_read(self, s_arg=None):
        if s_arg is not None:
            assert isinstance(s_arg, SomeInteger)
        return SomeString(can_be_None=False)

    def method_close(self):
        pass

    def method_seek(self, s_arg, s_whence=None):
        assert isinstance(s_arg, SomeInteger)
        if s_whence is not None:
            assert isinstance(s_whence, SomeInteger)

    def rtyper_makekey(self):
        return self.__class__,

    def rtyper_makerepr(self, rtyper):
        from rpython.rtyper.lltypesystem.rfile import FileRepr

        return FileRepr(rtyper)

class FileEntry(ExtRegistryEntry):
    _about_ = open

    def compute_result_annotation(self, s_name, s_mode=None):
        assert isinstance(s_name, SomeString)
        if s_mode is not None:
            assert isinstance(s_mode, SomeString)
        return SomeFile()

    def specialize_call(self, hop):
        return hop.r_result.rtype_constructor(hop)

class OSTempfileEntry(ExtRegistryEntry):
    _about_ = os.tmpfile

    def compute_result_annotation(self):
        return SomeFile()

    def specialize_call(self, hop):
        return hop.r_result.rtype_tempfile(hop)

