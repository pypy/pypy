#define _GNU_SOURCE 1

#include "utf8.h"
#include <stdio.h>
#include <assert.h>

#include "utf8-scalar.c" // copy code for scalar operations


int instruction_set = -1;
#define ISET_SSE4 0x1
#define ISET_AVX 0x2
#define ISET_AVX2 0x4

#if __x86_64__
void detect_instructionset(void)
{
    long eax;
    long ebx;
    long ecx;
    long edx;
    long op = 1;
    asm ("cpuid"
            : "=a" (eax),
              "=b" (ebx),
              "=c" (ecx),
              "=d" (edx)
            : "a" (op));

    __builtin_cpu_init();
    instruction_set = 0;
    if (ecx & (1<<19)) { // sse4.1
        instruction_set |= ISET_SSE4;
    }
    if(__builtin_cpu_supports("avx")) {
        instruction_set |= ISET_AVX;
    }
    if(__builtin_cpu_supports("avx2")) {
        instruction_set |= ISET_AVX2;
    }
}
#else
void detect_instructionset(void)
{
    // do nothing on other architectures
}
#endif

ssize_t fu8_count_utf8_codepoints(const char * utf8, size_t len)
{
    // assumption: utf8 is always a correctly encoded, if not return any result.
    if (instruction_set == -1) {
        detect_instructionset();
    }

    if (len >= 32 && (instruction_set & ISET_AVX2) != 0) {
        // to the MOON!
        return fu8_count_utf8_codepoints_avx(utf8, len);
    }
    if (len >= 16 && (instruction_set & ISET_SSE4) != 0) {
        // speed!!
        return fu8_count_utf8_codepoints_sse4(utf8, len);
    }

    // oh no, just do it sequentially!
    return fu8_count_utf8_codepoints_seq(utf8, len);
}

