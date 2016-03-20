#define HAVE_SYS_UCONTEXT_H
#if defined(__FreeBSD__)
#if defined(__i386__)
#define PC_FROM_UCONTEXT uc_mcontext.mc_eip
#else
#define PC_FROM_UCONTEXT uc_mcontext.mc_rip
#endif
#elif defined(__APPLE__)
#define PC_FROM_UCONTEXT uc_mcontext.mc_rip
#else
#define PC_FROM_UCONTEXT uc_mcontext.gregs[REG_RIP]
#endif
