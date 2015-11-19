#define HAVE_SYS_UCONTEXT_H
#if defined(__FreeBSD__) || defined(__APPLE__)
#define PC_FROM_UCONTEXT uc_mcontext.mc_rip
#else
#define PC_FROM_UCONTEXT uc_mcontext.gregs[REG_RIP]
#endif
