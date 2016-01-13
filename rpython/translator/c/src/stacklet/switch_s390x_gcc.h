#if !(defined(__LITTLE_ENDIAN__) ^ defined(__BIG_ENDIAN__))
# error "cannot determine if it is ppc64 or ppc64le"
#endif

#ifdef __BIG_ENDIAN__
# define TOC_AREA   "40"
#else
# define TOC_AREA   "24"
#endif


/* This depends on these attributes so that gcc generates a function
   with no code before the asm, and only "blr" after. */
static __attribute__((noinline, optimize("O2")))
void *slp_switch(void *(*save_state)(void*, void*),
                 void *(*restore_state)(void*, void*),
                 void *extra)
{
  void *result;
  __asm__ volatile (
     /* By Vaibhav Sood & Armin Rigo, with some copying from
        the Stackless version by Kristjan Valur Jonsson */

     /* Save all 18 volatile GP registers, 18 volatile FP regs, and 12
        volatile vector regs.  We need a stack frame of 144 bytes for FPR,
        144 bytes for GPR, 192 bytes for VR plus 48 bytes for the standard
        stackframe = 528 bytes (a multiple of 16). */

     //"mflr  0\n"               /* Save LR into 16(r1) */
     //"stg  0, 16(1)\n"

     "stmg 6,15,48(15)\n"

     "std 0,128(15)\n"
     "std 2,136(15)\n"
     "std 4,144(15)\n"
     "std 6,152(15)\n"

     "lay 15,-160(15)\n"         /* Create stack frame             */

     "lgr 10, %[restore_state]\n" /* save 'restore_state' for later */
     "lgr 11, %[extra]\n"         /* save 'extra' for later */
     "lgr 14, %[save_state]\n"    /* move 'save_state' into r14 for branching */
     "mr 2, 15\n"                 /* arg 1: current (old) stack pointer */
     "mr 3, 11\n"                /* arg 2: extra                       */

     "stdu 1, -48(1)\n"       /* create temp stack space (see below) */
#ifdef __BIG_ENDIAN__
     "ld 0, 0(12)\n"
     "ld 11, 16(12)\n"
     "mtctr 0\n"
     "ld 2, 8(12)\n"
#else
     "mtctr 12\n"             /* r12 is fixed by this ABI           */
#endif
     "bctrl\n"                /* call save_state()                  */
     "addi 1, 1, 48\n"        /* destroy temp stack space           */

     "CGIJ 2, 0, 7, zero\n"   /* skip the rest if the return value is null */

     "lgr 15, 2\n"              /* change the stack pointer */
       /* From now on, the stack pointer is modified, but the content of the
        stack is not restored yet.  It contains only garbage here. */

     "mr 4, 15\n"             /* arg 2: extra                       */
                              /* arg 1: current (new) stack pointer
                                 is already in r3                   */

     "stdu 1, -48(1)\n"       /* create temp stack space for callee to use  */
     /* ^^^ we have to be careful. The function call will store the link
        register in the current frame (as the ABI) dictates. But it will
        then trample it with the restore! We fix this by creating a fake
        stack frame */

#ifdef __BIG_ENDIAN__
     "ld 0, 0(14)\n"          /* 'restore_state' is in r14          */
     "ld 11, 16(14)\n"
     "mtctr 0\n"
     "ld 2, 8(14)\n"
#endif
#ifdef __LITTLE_ENDIAN__
     "mr 12, 14\n"            /* copy 'restore_state'               */
     "mtctr 12\n"             /* r12 is fixed by this ABI           */
#endif

     "bctrl\n"                /* call restore_state()               */
     "addi 1, 1, 48\n"        /* destroy temp stack space           */

     /* The stack's content is now restored. */

     "zero:\n"

     /* Epilogue */

     // "mtcrf 0xff, 12\n"

     // "addi 1,1,528\n"         

     "lay 15,160(15)\n"       /* restore stack pointer */

     "ld 0,128(15)\n"
     "ld 2,136(15)\n"
     "ld 4,144(15)\n"
     "ld 6,152(15)\n"

     "lmg 6,15,48(15)\n"

     : "=r"(result)         /* output variable: expected to be r2 */
     : [restore_state]"r"(restore_state),       /* input variables */
       [save_state]"r"(save_state),
       [extra]"r"(extra)
  );
  return result;
}
