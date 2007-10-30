/* This optional file only works for GCC on an i386.
 * It replaces some complex macros with native assembler instructions.
 */

#undef OP_INT_ADD_OVF
#define OP_INT_ADD_OVF(x,y,r)                   \
    asm volatile("addl %2,%0\n\t"               \
        "jno 0f\n\t"                            \
        "pusha\n\t"                             \
        "call op_int_overflowed\n\t"            \
        "popa\n\t"                              \
        "0:"                                    \
        : "=r"(r)            /* outputs */      \
        : "0"(x), "g"(y)     /* inputs  */      \
        : "cc", "memory")    /* clobber */

#undef OP_INT_ADD_NONNEG_OVF
#define OP_INT_ADD_NONNEG_OVF(x,y,r) OP_INT_ADD_OVF(x,y,r)

#undef OP_INT_SUB_OVF
#define OP_INT_SUB_OVF(x,y,r)                   \
    asm volatile("subl %2,%0\n\t"               \
        "jno 0f\n\t"                            \
        "pusha\n\t"                             \
        "call op_int_overflowed\n\t"            \
        "popa\n\t"                              \
        "0:"                                    \
        : "=r"(r)            /* outputs */      \
        : "0"(x), "g"(y)     /* inputs  */      \
        : "cc", "memory")    /* clobber */

#undef OP_INT_MUL_OVF
#define OP_INT_MUL_OVF(x,y,r)                   \
    asm volatile("imull %2,%0\n\t"              \
        "jno 0f\n\t"                            \
        "pusha\n\t"                             \
        "call op_int_overflowed\n\t"            \
        "popa\n\t"                              \
        "0:"                                    \
        : "=r"(r)            /* outputs */      \
        : "0"(x), "g"(y)     /* inputs  */      \
        : "cc", "memory")    /* clobber */


/* prototypes */

extern void op_int_overflowed(void)
     asm ("op_int_overflowed")
     __attribute__((used));

/* implementations */

#ifndef PYPY_NOT_MAIN_FILE

void op_int_overflowed(void)
{
  FAIL_OVF("integer operation");
}

#endif
