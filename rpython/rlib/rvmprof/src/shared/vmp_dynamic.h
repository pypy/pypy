#pragma once

#include <stdint.h>
#include <libunwind.h>

int vmp_dyn_register_jit_page(intptr_t addr, intptr_t end_addr,
                              const char * name);
int vmp_dyn_cancel(int ref);
int vmp_dyn_teardown(void);

