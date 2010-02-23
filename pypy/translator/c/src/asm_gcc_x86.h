/* This optional file only works for GCC on an i386.
 * It replaces some complex macros with native assembler instructions.
 */

#undef OP_INT_ADD_OVF
#define OP_INT_ADD_OVF(x,y,r)                   \
    asm volatile(                               \
        "/* ignore_in_trackgcroot */\n\t"       \
        "addl %2,%0\n\t"                        \
        "jno 0f\n\t"                            \
        "pusha\n\t"                             \
        "call _op_int_overflowed\n\t"           \
        "popa\n\t"                              \
        "0:\n\t"                                \
        "/* end_ignore_in_trackgcroot */"       \
        : "=r"(r)            /* outputs */      \
        : "0"(x), "g"(y)     /* inputs  */      \
        : "cc", "memory")    /* clobber */

#undef OP_INT_ADD_NONNEG_OVF
#define OP_INT_ADD_NONNEG_OVF(x,y,r) OP_INT_ADD_OVF(x,y,r)

#undef OP_INT_SUB_OVF
#define OP_INT_SUB_OVF(x,y,r)                   \
    asm volatile(                               \
        "/* ignore_in_trackgcroot */\n\t"       \
        "subl %2,%0\n\t"                        \
        "jno 0f\n\t"                            \
        "pusha\n\t"                             \
        "call _op_int_overflowed\n\t"           \
        "popa\n\t"                              \
        "0:\n\t"                                \
        "/* end_ignore_in_trackgcroot */"       \
        : "=r"(r)            /* outputs */      \
        : "0"(x), "g"(y)     /* inputs  */      \
        : "cc", "memory")    /* clobber */

#undef OP_INT_MUL_OVF
#define OP_INT_MUL_OVF(x,y,r)                   \
    asm volatile(                               \
        "/* ignore_in_trackgcroot */\n\t"       \
        "imull %2,%0\n\t"                       \
        "jno 0f\n\t"                            \
        "pusha\n\t"                             \
        "call _op_int_overflowed\n\t"           \
        "popa\n\t"                              \
        "0:\n\t"                                \
        "/* end_ignore_in_trackgcroot */"       \
        : "=r"(r)            /* outputs */      \
        : "0"(x), "g"(y)     /* inputs  */      \
        : "cc", "memory")    /* clobber */

/* Pentium only! */
#define READ_TIMESTAMP(val) \
     asm volatile("rdtsc" : "=A" (val))
// Kernel has a barrier around rtdsc 
// mfence
// lfence
// rtdsc
// mfence
// lfence
// I don't know how important it is, comment talks about time warps


/* prototypes */

extern void op_int_overflowed(void)
     asm ("_op_int_overflowed")
     __attribute__((used));

/* implementations */

#ifndef PYPY_NOT_MAIN_FILE

void op_int_overflowed(void)
{
  FAIL_OVF("integer operation");
}

#endif
