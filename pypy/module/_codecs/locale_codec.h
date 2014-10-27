#include <stdlib.h>
#include <wchar.h>
#include "src/precommondefs.h"

RPY_EXPORTED_FOR_TESTS wchar_t* pypy_char2wchar(const char* arg, size_t *size);
RPY_EXPORTED_FOR_TESTS void pypy_char2wchar_free(wchar_t *text);
RPY_EXPORTED_FOR_TESTS char* pypy_wchar2char(const wchar_t *text, size_t *error_pos);
RPY_EXPORTED_FOR_TESTS void pypy_wchar2char_free(char *bytes);
