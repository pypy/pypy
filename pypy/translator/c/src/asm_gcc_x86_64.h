/* This optional file only works for GCC on an x86-64.
 */

#define READ_TIMESTAMP(val) do {                        \
    unsigned new_long _rax, _rdx;                           \
    asm volatile("rdtsc" : "=a"(_rax), "=d"(_rdx)); \
    val = (_rdx << 32) | _rax;                          \
} while (0)
