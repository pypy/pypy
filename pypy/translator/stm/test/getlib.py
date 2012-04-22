from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.translator.stm.stmgcintf import eci


src_code = r'''

struct pypy_header0 {
    long h_tid;
    void *h_version;
};

struct pypy_pypy_rlib_rstm_Transaction0 {
    struct pypy_header0 header;
    struct pypy_pypy_rlib_rstm_Transaction0 *t_inst__next_transaction;
};


#include "src_stm/et.h"
#include "src_stm/et.c"


void (*stm_thread_starting)(void);
void (*stm_thread_stopping)(void);
void *(*stm_run_transaction)(void *, long);
long (*stm_getsize)(void *);
void (*stm_enum_callback)(void *, void *, void *);


void pypy_g__stm_thread_starting(void) {
    stm_thread_starting();
}
void pypy_g__stm_thread_stopping(void) {
    stm_thread_stopping();
}
void *pypy_g__stm_run_transaction(void *a, long b) {
    return stm_run_transaction(a, b);
}
long pypy_g__stm_getsize(void *a) {
    return stm_getsize(a);
}
void pypy_g__stm_enum_callback(void *a, void *b, void *c) {
    stm_enum_callback(a, b, c);
}
'''


assert not hasattr(eci, '_with_ctypes')

eci._with_ctypes = eci.merge(ExternalCompilationInfo(
    separate_module_sources = [src_code],
    ))
