from pypy.rpython.lltypesystem import lltype, rffi
from pypy.rlib.rarithmetic import intmask
from pypy.rlib.debug import debug_start, debug_print, debug_stop
from pypy.rlib.debug import have_debug_prints
from pypy.jit.backend.llsupport.asmmemmgr import BlockBuilderMixin
from pypy.jit.backend.x86.rx86 import X86_32_CodeBuilder, X86_64_CodeBuilder
from pypy.jit.backend.x86.regloc import LocationCodeBuilder
from pypy.jit.backend.x86.arch import IS_X86_32, IS_X86_64, WORD
from pypy.jit.backend.x86 import valgrind

# XXX: Seems nasty to change the superclass of MachineCodeBlockWrapper
# like this
if IS_X86_32:
    codebuilder_cls = X86_32_CodeBuilder
    backend_name = 'x86'
elif IS_X86_64:
    codebuilder_cls = X86_64_CodeBuilder
    backend_name = 'x86_64'


class MachineCodeBlockWrapper(BlockBuilderMixin,
                              codebuilder_cls,
                              LocationCodeBuilder):
    def __init__(self):
        self.init_block_builder()
        # a list of relative positions; for each position p, the bytes
        # at [p-4:p] encode an absolute address that will need to be
        # made relative.
        self.relocations = []
        self.labels = []

    def add_pending_relocation(self):
        self.relocations.append(self.get_relative_pos())

    def mark_label(self, name):
        pos = self.get_relative_pos()
        self.labels.append((pos, name))

    def copy_to_raw_memory(self, addr):
        self._copy_to_raw_memory(addr)
        for reloc in self.relocations:
            p = addr + reloc
            adr = rffi.cast(rffi.LONGP, p - WORD)
            adr[0] = intmask(adr[0] - p)
        valgrind.discard_translations(addr, self.get_relative_pos())
        self._dump(addr, "jit-backend-dump", backend_name)
        self.dump_labels(addr, "jit-backend-dump-labels")

    def dump_labels(self, addr, logname):
        debug_start(logname)
        if have_debug_prints():
            debug_print('LABELS @%x' % addr)
            for offset, name in self.labels:
                debug_print('+%d: %s' % (offset, name))
        debug_stop(logname)

