
static void __attribute__((optimize("O2"))) *slp_switch(void *(*save_state)(void*, void*),
                        void *(*restore_state)(void*, void*),
                        void *extra)
{
  void *result;
  __asm__ volatile (
     /*Prologue: Save explicitly lr and some non-volatile registers used by compiler in caller code */
     "mflr 0\n"
     "std 0, 16(1)\n"
     "std 31, -8(1)\n"
     "std 30, -16(1)\n"
     "std 29, -24(1)\n"
     "std 28, -32(1)\n"
     "stdu 1, -176(1)\n"         /* 48(save area) + 64(parameter area) + 64(non-volatile save area) = 176 bytes */
                                 /* stack is implicitly 16-byte aligned */

     "mr 14, %[restore_state]\n" /* save 'restore_state' for later, r14 marked clobbered */
     "mr 15, %[extra]\n"         /* save 'extra' for later, r15 marked clobbered */
     
     "mtlr %[save_state]\n"    /* save 'save_state' for branching */
     "mr 3, 1\n"               /* arg 1: current (old) stack pointer */ 
     "mr 4, %[extra]\n"        /* arg 2: extra                       */
     "stdu 1, -64(1)\n"        /* create temp stack space for callee to use  */
     "blrl\n"                  /* call save_state()                  */
     "nop\n"
     "addi 1, 1, 64\n"         /* destroy temp stack space */

     "cmpdi 3, 0\n"           /* skip the rest if the return value is null */
     "bt eq, zero\n"

     "mr 1, 3\n"              /* change the stack pointer */
       /* From now on, the stack pointer is modified, but the content of the
        stack is not restored yet.  It contains only garbage here. */

     "mr 5, 14\n"
     "mtlr 5\n"
     "mr 4, 15\n"             /* arg 2: extra                       */
                              /* arg 1: current (new) stack pointer is already in r3*/

     "stdu 1, -64(1)\n"       /* create temp stack space for callee to use  */
     "blrl\n"                 /* call restore_state()               */
     "nop\n"
     "addi 1, 1, 64\n"        /* destroy temp stack space */

     /* The stack's content is now restored. */

     "zero:\n"
     /* Epilogue: Restore sp, lr and saved non-volatile registers */
     "ld 1, 0(1)\n"
     "ld 0, 16(1)\n"
     "mtlr 0\n"
     "ld 28, -32(1)\n"
     "ld 29, -24(1)\n"
     "ld 30, -16(1)\n"
     "ld 31, -8(1)\n"
     : [result]"=r"(result)             /* output variables */
     : [restore_state]"r"(restore_state),       /* input variables  */
       [save_state]"r"(save_state),
       [extra]"r"(extra)
     : "r0", "r4", "r5", "r14", "r15", "memory"
  );
  return result;
}
