#define HAVE_SYS_UCONTEXT_H
#if defined(__FreeBSD__) || defined(__FreeBSD_kernel__)
  #ifdef __i386__
    #define PC_FROM_UCONTEXT uc_mcontext.mc_eip
  #else
    #define PC_FROM_UCONTEXT uc_mcontext.mc_rip
  #endif
#elif defined( __APPLE__)
  #if ((ULONG_MAX) == (UINT_MAX))
    #define PC_FROM_UCONTEXT uc_mcontext->__ss.__eip
  #else
    #define PC_FROM_UCONTEXT uc_mcontext->__ss.__rip
  #endif
#elif defined(__arm__)
  #define PC_FROM_UCONTEXT uc_mcontext.arm_ip
#elif defined(__linux) && defined(__i386) && defined(__GNUC__)
  #define PC_FROM_UCONTEXT uc_mcontext.gregs[REG_EIP]
#else
  /* linux, gnuc */
  #define PC_FROM_UCONTEXT uc_mcontext.gregs[REG_RIP]
#endif
