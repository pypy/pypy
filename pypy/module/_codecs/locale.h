#include <stdlib.h>
#include <wchar.h>

wchar_t* pypy_char2wchar(const char* arg, size_t *size);
void pypy_char2wchar_free(wchar_t *text);
char* pypy_wchar2char(const wchar_t *text, size_t *error_pos);
void pypy_wchar2char_free(char *bytes);
