from rpython.rlib import rthread


def get_thread_ident_offset(cpu):
    assert cpu.translate_support_code
    return rthread.tlfield_thread_ident.getoffset()
