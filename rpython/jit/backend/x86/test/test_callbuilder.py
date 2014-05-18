from rpython.jit.backend.x86 import callbuilder
from rpython.jit.backend.x86.regloc import esi, edi, ebx, ecx, ImmedLoc


class FakeAssembler:
    mc = None
    class _regalloc:
        class rm:
            free_regs = [ebx]

    def __init__(self):
        self._log = []

    def _is_asmgcc(self):
        return False

    def regalloc_mov(self, src, dst):
        self._log.append(('mov', src, dst))


def test_base_case():
    asm = FakeAssembler()
    cb = callbuilder.CallBuilder64(asm, ImmedLoc(12345), [ebx, ebx])
    cb.prepare_arguments()
    assert asm._log == [('mov', ebx, edi),
                        ('mov', ebx, esi)]

def test_bug_call_release_gil():
    asm = FakeAssembler()
    cb = callbuilder.CallBuilder64(asm, ImmedLoc(12345), [ebx, ebx])
    cb.select_call_release_gil_mode()
    cb.prepare_arguments()
    assert asm._log == [('mov', ebx, ecx)]
