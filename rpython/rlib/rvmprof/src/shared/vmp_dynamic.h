#pragma once

#include <stdint.h>
#include <libunwind.h>

#include "rvmprof.h"

RPY_EXTERN int vmp_dyn_register_jit_page(intptr_t addr, intptr_t end_addr,
                              const char * name);
RPY_EXTERN int vmp_dyn_cancel(int ref);
RPY_EXTERN int vmp_dyn_teardown(void);

