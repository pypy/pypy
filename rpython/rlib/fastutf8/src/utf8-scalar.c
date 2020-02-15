#include "utf8.h"

int _check_continuation(const uint8_t ** encoded, const uint8_t * endptr, int count) {
    ssize_t size = endptr - *encoded;

    if (size < count) {
        // not enough bytes to be a valid 2 byte utf8 code point
        return -1;
    }
    for (int i = 0; i < count; i++) {
        uint8_t byte = *(*encoded)++;
        if ((byte & 0xc0) != 0x80) { 
            // continuation byte does NOT match 0x10xxxxxx
            return -1;
        }
    }
    return 0;
}

ssize_t fu8_count_utf8_codepoints_seq(const char * utf8, size_t len) {
    size_t num_codepoints = 0;
    const char * encoded = utf8;
    const char * endptr = encoded + len;

    while (encoded < endptr) {
        if (*encoded++ >= -0x40) {
            num_codepoints++;
        }
    }
    return num_codepoints;
}
