#include "utf8.h"

#include <stddef.h>
#include <stdio.h>
#include <stdint.h>
#include <xmmintrin.h>
#include <smmintrin.h>

#define BIT(B,P) ((B >> (P-1)) & 0x1)

void _print_mmx(const char * msg, __m128i chunk)
{
    printf("%s:", msg);
    // unpack the first 8 bytes, padding with zeros
    uint64_t a = _mm_extract_epi64(chunk, 0);
    uint64_t b = _mm_extract_epi64(chunk, 1);
    printf("%.2x%.2x%.2x%.2x %.2x%.2x%.2x%.2x  %.2x%.2x%.2x%.2x %.2x%.2x%.2x%.2x",
            (unsigned char)((a >> 0) & 0xff),
            (unsigned char)((a >> 8) & 0xff),
            (unsigned char)((a >> 16) & 0xff),
            (unsigned char)((a >> 24) & 0xff),

            (unsigned char)((a >> 32) & 0xff),
            (unsigned char)((a >> 40) & 0xff),
            (unsigned char)((a >> 48) & 0xff),
            (unsigned char)((a >> 56) & 0xff),

            (unsigned char)((b >> 0) & 0xff),
            (unsigned char)((b >> 8) & 0xff),
            (unsigned char)((b >> 16) & 0xff),
            (unsigned char)((b >> 24) & 0xff),

            (unsigned char)((b >> 32) & 0xff),
            (unsigned char)((b >> 40) & 0xff),
            (unsigned char)((b >> 48) & 0xff),
            (unsigned char)((b >> 56) & 0xff)
     );

    printf("\n");
}


ssize_t fu8_count_utf8_codepoints_sse4(const char * utf8, size_t len)
{
    const char * encoded = utf8;
    __builtin_prefetch(encoded, 0, 0);
    size_t num_codepoints = 0;
    __m128i chunk;

    if (len == 0) {
        return 0;
    }
    while (len >= 16) {
        chunk = _mm_loadu_si128((__m128i*)encoded);
        if (_mm_movemask_epi8(chunk) == 0) {
            // valid ascii chars!
            len -= 16;
            encoded += 16;
            num_codepoints += 16;
            continue;
        }
        __builtin_prefetch(encoded+16, 0, 0);

        // there is no comparison on unsigned values
        __m128i count = _mm_cmplt_epi8(_mm_set1_epi8(-0x41), chunk);
        int mask = _mm_movemask_epi8(count);
        int bitcount = __builtin_popcount(mask);
        len -= 16;
        encoded += 16;
        num_codepoints += bitcount;
    }

    if (len == 0) {
        return num_codepoints;
    }

    ssize_t result = fu8_count_utf8_codepoints_seq(encoded, len);
    if (result == -1) {
        return -1;
    }

    return num_codepoints + result;
}
