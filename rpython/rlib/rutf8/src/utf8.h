#pragma once

#include <unistd.h>
#include <stdint.h>
#include <stddef.h>

/**
 * Returns -1 if the given string is not a valid utf8 encoded string.
 * Otherwise returns the amount code point in the given string.
 * len: length in bytes (8-bit)
 *
 * The above documentation also applies for several vectorized implementations
 * found below.
 *
 * count_utf8_codepoints dispatches amongst several
 * implementations (e.g. seq, SSE4, AVX)
 */
// TODO rename (fu8 prefix)
ssize_t fu8_count_utf8_codepoints(const uint8_t * encoded, size_t len);
ssize_t fu8_count_utf8_codepoints_seq(const uint8_t * encoded, size_t len);
ssize_t fu8_count_utf8_codepoints_sse4(const uint8_t * encoded, size_t len);
ssize_t fu8_count_utf8_codepoints_avx(const uint8_t * encoded, size_t len);


struct fu8_idxtab;

/**
 * Looks up the byte position of the utf8 code point at the index.
 * Assumptions:
 *
 *  * utf8 parameter is utf8 encoded, otherwise the result is undefined.
 *  * passing one struct fu8_idxtab instance to several different utf8 strings
 *    yields undefined behaviour
 *
 * Return values:
 *
 * -1, if the index is out of bounds of utf8
 *  X, where X >= 0. X is the byte postion for the code point at index
 *
 * If table is not NULL, this routine builds up a lookup
 * table to speed up indexing.
 *
 */
ssize_t fu8_idx2bytepos(size_t index,
                        const uint8_t * utf8, size_t bytelen,
                        size_t cplen,
                        struct fu8_idxtab ** tab);
void fu8_free_idxtab(struct fu8_idxtab * t);
ssize_t fu8_idx2bytepso_sse4(size_t index,
                             const uint8_t * utf8, size_t len,
                             struct fu8_idxtab ** t);
