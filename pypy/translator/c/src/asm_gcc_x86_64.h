/* This optional file only works for GCC on an x86-64.
 */

#define READ_TIMESTAMP(val) do {                        \
    unsigned int _eax, _edx;                            \
    asm volatile("rdtsc" : "=a" (_eax), "=d" (_edx));   \
    val = (((unsigned long) _edx) << 32) | _eax;        \
} while (0)
