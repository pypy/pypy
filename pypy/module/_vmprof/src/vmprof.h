#ifndef VMPROF_VMPROF_H_
#define VMPROF_VMPROF_H_

#include <stddef.h>
#include <stdint.h>
#include <ucontext.h>

// copied from libunwind.h

typedef enum
  {
    UNW_X86_64_RAX,
    UNW_X86_64_RDX,
    UNW_X86_64_RCX,
    UNW_X86_64_RBX,
    UNW_X86_64_RSI,
    UNW_X86_64_RDI,
    UNW_X86_64_RBP,
    UNW_X86_64_RSP,
    UNW_X86_64_R8,
    UNW_X86_64_R9,
    UNW_X86_64_R10,
    UNW_X86_64_R11,
    UNW_X86_64_R12,
    UNW_X86_64_R13,
    UNW_X86_64_R14,
    UNW_X86_64_R15,
    UNW_X86_64_RIP,
#ifdef CONFIG_MSABI_SUPPORT
    UNW_X86_64_XMM0,
    UNW_X86_64_XMM1,
    UNW_X86_64_XMM2,
    UNW_X86_64_XMM3,
    UNW_X86_64_XMM4,
    UNW_X86_64_XMM5,
    UNW_X86_64_XMM6,
    UNW_X86_64_XMM7,
    UNW_X86_64_XMM8,
    UNW_X86_64_XMM9,
    UNW_X86_64_XMM10,
    UNW_X86_64_XMM11,
    UNW_X86_64_XMM12,
    UNW_X86_64_XMM13,
    UNW_X86_64_XMM14,
    UNW_X86_64_XMM15,
    UNW_TDEP_LAST_REG = UNW_X86_64_XMM15,
#else
    UNW_TDEP_LAST_REG = UNW_X86_64_RIP,
#endif

    /* XXX Add other regs here */

    /* frame info (read-only) */
    UNW_X86_64_CFA,

    UNW_TDEP_IP = UNW_X86_64_RIP,
    UNW_TDEP_SP = UNW_X86_64_RSP,
    UNW_TDEP_BP = UNW_X86_64_RBP,
    UNW_TDEP_EH = UNW_X86_64_RAX
  }
x86_64_regnum_t;

typedef uint64_t unw_word_t;

#define UNW_TDEP_CURSOR_LEN 127

typedef struct unw_cursor
  {
    unw_word_t opaque[UNW_TDEP_CURSOR_LEN];
  }
unw_cursor_t;

#define UNW_REG_IP UNW_X86_64_RIP
#define UNW_REG_SP UNW_X86_64_RSP

typedef ucontext_t unw_context_t;

typedef struct unw_proc_info
  {
    unw_word_t start_ip;	/* first IP covered by this procedure */
    unw_word_t end_ip;		/* first IP NOT covered by this procedure */
    unw_word_t lsda;		/* address of lang.-spec. data area (if any) */
    unw_word_t handler;		/* optional personality routine */
    unw_word_t gp;		/* global-pointer value for this procedure */
    unw_word_t flags;		/* misc. flags */

    int format;			/* unwind-info format (arch-specific) */
    int unwind_info_size;	/* size of the information (if applicable) */
    void *unwind_info;		/* unwind-info (arch-specific) */
  }
unw_proc_info_t;

// functions copied from libunwind using dlopen

extern int (*unw_get_reg)(unw_cursor_t*, int, unw_word_t*);
extern int (*unw_step)(unw_cursor_t*);
extern int (*unw_init_local)(unw_cursor_t *, unw_context_t *);
extern int (*unw_get_proc_info)(unw_cursor_t *, unw_proc_info_t *);

// end of copy

extern char* vmprof_error;

typedef void* (*vmprof_get_virtual_ip_t)(void*);
char* vmprof_get_error();

extern void* vmprof_mainloop_func;
int vmprof_set_mainloop(void* func, ptrdiff_t sp_offset, 
                         vmprof_get_virtual_ip_t get_virtual_ip);

void vmprof_register_virtual_function(const char* name, void* start, void* end);


int vmprof_enable(int fd, long period_usec, int write_header, char* vips,
				  int vips_len);
int vmprof_disable(void);

// XXX: this should be part of _vmprof (the CPython extension), not vmprof (the library)
void vmprof_set_tramp_range(void* start, void* end);

#endif
