#if defined(__ARM_ARCH_4__) || defined (__ARM_ARCH_4T__)
# define call_reg(x) "mov lr, pc ; bx " #x "\n"
#else
/* ARM >= 5 */
# define call_reg(x) "blx " #x "\n"
#endif

static void *slp_switch(void *(*save_state)(void*, void*),
                        void *(*restore_state)(void*, void*),
                        void *extra)
{
  void *result;
  /*
      seven registers to preserve: r2, r3, r7, r8, r9, r10, r11
      registers marked as clobbered: r0, r1, r4, r5, r6, r12, lr
      others: r13 is sp; r14 is lr; r15 is pc
  */

  __asm__ volatile (

    /* align the stack and save 7 more registers explicitly */
    "mov r0, sp\n"
    "and r1, r0, #-16\n"
    "mov sp, r1\n"
    "push {r0, r2, r3, r7, r8, r9, r10, r11}\n"   /* total 8, still aligned */

    /* save values in callee saved registers for later */
    "mov r4, %[restore_state]\n"  /* can't be r0 or r1: marked clobbered */
    "mov r5, %[extra]\n"          /* can't be r0 or r1 or r4: marked clob. */
    "mov r3, %[save_state]\n"     /* can't be r0, r1, r4, r5: marked clob. */
    "mov r0, sp\n"        	/* arg 1: current (old) stack pointer */
    "mov r1, r5\n"        	/* arg 2: extra                       */
    call_reg(r3)		/* call save_state()                  */

    /* skip the rest if the return value is null */
    "cmp r0, #0\n"
    "beq zero\n"

    "mov sp, r0\n"			/* change the stack pointer */

	/* From now on, the stack pointer is modified, but the content of the
	stack is not restored yet.  It contains only garbage here. */
    "mov r1, r5\n"       	/* arg 2: extra                       */
                /* arg 1: current (new) stack pointer is already in r0*/
    call_reg(r4)		/* call restore_state()               */

    /* The stack's content is now restored. */
    "zero:\n"

    "pop {r1, r2, r3, r7, r8, r9, r10, r11}\n"
    "mov sp, r1\n"
    "mov %[result], r0\n"

    : [result]"=r"(result)	/* output variables */
	/* input variables  */
    : [restore_state]"r"(restore_state),
      [save_state]"r"(save_state),
      [extra]"r"(extra)
    : "r0", "r1", "r4", "r5", "r6", "r12", "lr",
      "memory", "cc"
#ifndef __SOFTFP__
      , "d0", "d1", "d2",  "d3",  "d4",  "d5",  "d6",  "d7"
      , "d8", "d9", "d10", "d11", "d12", "d13", "d14", "d15"
/* messsssssssssssss quite unsure it is the correct way */
/* Actually it seems there is no way.  These macros are defined by ARM's
 * own compiler but not by GCC.  On GCC, by looking at its sources it
 * seems that we'd like to know the internal TARGET_VFPD32 flag, but
 * there is no way to access it because it's not exported as a macro.
 * We loose.  If you compile for some architecture with 32 "d"
 * registers, gcc will likely move the registers to save (d8-d15)
 * into some of d16-d31, and they will then be clobbered.
 * I don't see any solution. :-((
 */
# if defined(__TARGET_FPU_SOFTVFP_VFPV3) || \
     defined(__TARGET_FPU_SOFTVFP_VFPV3_FP16) || \
     defined(__TARGET_FPU_VFPV3) || \
     defined(__TARGET_FPU_VFPV3_FP16) || \
     defined(__TARGET_FPU_VFPV4)
      , "d16", "d17", "d18", "d19", "d20", "d21", "d22", "d23"
      , "d24", "d25", "d26", "d27", "d28", "d29", "d30", "d31"
# endif
#endif
  );
  return result;
}
