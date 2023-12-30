#include "utf8.h"

#include <stddef.h>
#include <stdio.h>
#include <stdint.h>
#include <immintrin.h>

#define BIT(B,P) ((B >> (P-1)) & 0x1)

void _print_mm256x(const char * msg, __m256i chunk)
{
    printf("%s:\n", msg);
    // unpack the first 8 bytes, padding with zeros
    uint64_t a = _mm256_extract_epi64(chunk, 0);
    uint64_t b = _mm256_extract_epi64(chunk, 1);
    uint64_t c = _mm256_extract_epi64(chunk, 2);
    uint64_t d = _mm256_extract_epi64(chunk, 3);
    printf("%.2x%.2x%.2x%.2x %.2x%.2x%.2x%.2x  %.2x%.2x%.2x%.2x %.2x%.2x%.2x%.2x    "
           "%.2x%.2x%.2x%.2x %.2x%.2x%.2x%.2x  %.2x%.2x%.2x%.2x %.2x%.2x%.2x%.2x",
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
            (unsigned char)((b >> 56) & 0xff),

            (unsigned char)((c >> 0) & 0xff),
            (unsigned char)((c >> 8) & 0xff),
            (unsigned char)((c >> 16) & 0xff),
            (unsigned char)((c >> 24) & 0xff),

            (unsigned char)((c >> 32) & 0xff),
            (unsigned char)((c >> 40) & 0xff),
            (unsigned char)((c >> 48) & 0xff),
            (unsigned char)((c >> 56) & 0xff),

            (unsigned char)((d >> 0) & 0xff),
            (unsigned char)((d >> 8) & 0xff),
            (unsigned char)((d >> 16) & 0xff),
            (unsigned char)((d >> 24) & 0xff),

            (unsigned char)((d >> 32) & 0xff),
            (unsigned char)((d >> 40) & 0xff),
            (unsigned char)((d >> 48) & 0xff),
            (unsigned char)((d >> 56) & 0xff)
     );

    printf("\n");
}

ssize_t fu8_count_utf8_codepoints_avx(const char * utf8, size_t len)
{
    const char * encoded = utf8;
    __builtin_prefetch(encoded, 0, 0);
    size_t num_codepoints = 0;
    __m256i chunk;

    if (len == 0) {
        return 0;
    }
    while (len >= 32) {
        chunk = _mm256_loadu_si256((__m256i*)encoded);
        if (_mm256_movemask_epi8(chunk) == 0) {
            // valid ascii chars!
            len -= 32;
            encoded += 32;
            num_codepoints += 32;
            continue;
        }
        __builtin_prefetch(encoded+32, 0, 0);

        // fight against the fact that there is no comparison on unsigned values
        __m256i count = _mm256_cmpgt_epi8(chunk, _mm256_set1_epi8(-0x41));
        unsigned int mask = (unsigned int)_mm256_movemask_epi8(count);
        int bitcount = __builtin_popcount(mask);
        len -= 32;
        encoded += 32;
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
