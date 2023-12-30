#pragma once

#include <unistd.h>
#include <stdint.h>
#include <stddef.h>

#ifndef RPY_EXTERN
#  define RPY_EXTERN RPY_EXPORTED
#endif

#ifdef _WIN32
#ifndef RPY_EXPORTED
#define RPY_EXPORTED __declspec(dllexport)
#endif
#else
#  define RPY_EXPORTED  extern __attribute__((visibility("default")))
#endif

/**
 * Given valid utf8 encoded bytes, it returns the amount of code points.
 * Returns any result if the bytes are not encoded correctly.
 * len: length in bytes (8-bit)
 *
 * The above documentation also applies for several vectorized implementations
 * found below.
 *
 * fu8_count_utf8_codepoints dispatches amongst several
 * implementations (e.g. seq, SSE4, AVX)
 */
RPY_EXTERN ssize_t fu8_count_utf8_codepoints(const char * utf8, size_t len);
ssize_t fu8_count_utf8_codepoints_seq(const char * utf8, size_t len);
ssize_t fu8_count_utf8_codepoints_sse4(const char * utf8, size_t len);
ssize_t fu8_count_utf8_codepoints_avx(const char * utf8, size_t len);
