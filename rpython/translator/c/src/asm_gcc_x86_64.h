/* This optional file only works for GCC on an x86-64.
 */

#define READ_TIMESTAMP(val) do {                        \
    Unsigned _rax, _rdx;                           \
    asm volatile("rdtsc" : "=a"(_rax), "=d"(_rdx)); \
    val = (_rdx << 32) | _rax;                          \
} while (0)

#undef OP_LONG2_FLOORDIV
/* assumes that 'y' and 'r' fit in a signed word, 
   but 'x' takes up to two words */
#define OP_LONG2_FLOORDIV(x, y, r)    do {                      \
        long ignored;                                           \
        __asm__("idiv %2" : "=a"(r), "=d"(ignored) :            \
                "r"((long)y), "a"((long)x),                     \
                "d"((long)((x >> 32) >> 32)));                  \
    } while (0)
