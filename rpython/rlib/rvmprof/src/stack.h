#pragma once

#include "_vmprof.h"

int vmp_walk_and_record_stack(PyFrameObject *frame, void **data,
                              int max_depth, int native_skip);

int vmp_native_enabled(void);
int vmp_native_enable(void);
int vmp_ignore_ip(ptr_t ip);
int vmp_binary_search_ranges(ptr_t ip, ptr_t * l, int count);
int vmp_native_symbols_read(void);
void vmp_profile_lines(int lines);
int vmp_profiles_python_lines(void);

int vmp_ignore_symbol_count(void);
ptr_t * vmp_ignore_symbols(void);
void vmp_set_ignore_symbols(ptr_t * symbols, int count);
void vmp_native_disable(void);

#ifdef __unix__
int vmp_read_vmaps(const char * fname);
#endif
