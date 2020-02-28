#include "utf8.h"

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
