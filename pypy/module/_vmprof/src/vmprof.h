#ifndef VMPROF_VMPROF_H_
#define VMPROF_VMPROF_H_

#include <stddef.h>

typedef void* (*vmprof_get_virtual_ip_t)(void*);

extern void* vmprof_mainloop_func;
void vmprof_set_mainloop(void* func, ptrdiff_t sp_offset, 
                         vmprof_get_virtual_ip_t get_virtual_ip);

void vmprof_register_virtual_function(const char* name, void* start, void* end);


int vmprof_enable(int fd, long period_usec, int write_header, char* vips,
				  int vips_len);
int vmprof_disable(void);

// XXX: this should be part of _vmprof (the CPython extension), not vmprof (the library)
void vmprof_set_tramp_range(void* start, void* end);

#endif
