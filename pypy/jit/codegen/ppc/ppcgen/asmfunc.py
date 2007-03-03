import py
import mmap, struct

_ppcgen = None

def get_ppcgen():
    global _ppcgen
    if _ppcgen is None:
        _ppcgen = py.magic.autopath().dirpath().join('_ppcgen.c')._getpymodule()
    return _ppcgen

class AsmCode(object):
    def __init__(self, size):
        self.code = mmap.mmap(-1, size,
                              mmap.MAP_ANON|mmap.MAP_PRIVATE,
                              mmap.PROT_WRITE|mmap.PROT_READ|mmap.PROT_EXEC)
    def emit(self, insn):
        self.code.write(struct.pack('i', insn))
    def __call__(self, *args):
        return get_ppcgen().mmap_exec(self.code, args)
    def flush_cache(self):
        get_ppcgen().mmap_flush(self.code)

