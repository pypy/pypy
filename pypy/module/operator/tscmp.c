/* From CPython 3.3.5's operator.c
 */

#include <stdlib.h>
#include "tscmp.h"

int
pypy_tscmp(const unsigned char *a, const unsigned char *b, long len_a, long len_b)
{
    /* The volatile type declarations make sure that the compiler has no
     * chance to optimize and fold the code in any way that may change
     * the timing.
     */
    volatile long length;
    volatile const unsigned char *left;
    volatile const unsigned char *right;
    long i;
    unsigned char result;

    /* loop count depends on length of b */
    length = len_b;
    left = NULL;
    right = b;

    /* don't use else here to keep the amount of CPU instructions constant,
     * volatile forces re-evaluation
     *  */
    if (len_a == length) {
        left = *((volatile const unsigned char**)&a);
        result = 0;
    }
    if (len_a != length) {
        left = b;
        result = 1;
    }

    for (i=0; i < length; i++) {
        result |= *left++ ^ *right++;
    }

    return (result == 0);
}
