#include "debug_internal.h"

#if ((__linux__ && __GNU_LIBRARY__) || __APPLE__)

// Basic implementation that uses backtrace from glibc

#include <stdlib.h>
#include <string.h>
#include <execinfo.h>

static inline int max_s(size_t a, size_t b) {
    return a > b ? a : b;
}

void create_stacktrace(char **target, HPy_ssize_t max_frames_count) {
    const size_t skip_frames = 2;
    size_t max_stack_size = (size_t) max_frames_count;
    void* stack = calloc(sizeof(void*), max_stack_size);
    if (stack == NULL) {
        *target = NULL;
        return;
    }

    size_t stack_size = backtrace(stack, max_stack_size);
    if (stack_size <= skip_frames) {
        *target = NULL;
        free(stack);
        return;
    }

    char** symbols = backtrace_symbols(stack, stack_size);
    if (symbols == NULL) {
        *target = NULL;
        free(stack);
        return;
    }

    size_t buffer_size = 1024;
    size_t buffer_index = 0;
    char *buffer = malloc(buffer_size);
    if (buffer == NULL) {
        *target = NULL;
        free(symbols);
        free(stack);
        return;
    }

    size_t i;
    for (i = skip_frames; i < stack_size; ++i) {
        size_t current_len = strlen(symbols[i]);
        size_t required_buffer_size = buffer_index + current_len + 1;
        if (required_buffer_size > buffer_size) {
            buffer_size = max_s(buffer_size * 2, required_buffer_size);
            char *new_buffer = realloc(buffer, buffer_size);
            if (new_buffer == NULL) {
                // allocation failed, we can still provide at least part of
                // the stack trace that is currently in the buffer
                break;
            }
            buffer = new_buffer;
        }
        memcpy(buffer + buffer_index, symbols[i], current_len);
        buffer[buffer_index + current_len] = '\n';
        buffer_index = required_buffer_size;
    }

    // override the last '\n' to '\0'
    assert(stack_size - skip_frames > 0);
    assert(buffer[buffer_index - 1] == '\n');
    buffer[buffer_index - 1] = '\0';
    char *shorter_buffer = realloc(buffer, buffer_index);
    if (shorter_buffer != NULL) {
        buffer = shorter_buffer;
    }
    *target = buffer;

    free(symbols);
    free(stack);
}

#else

#include <string.h>

void create_stacktrace(char **target, HPy_ssize_t max_frames_count) {
    const char msg[] =
            "Current HPy build does not support getting C stack traces.\n"
            "At the moment this is only supported on Linux with glibc"
            " and macOS.";
    *target = malloc(sizeof(msg));
    memcpy(*target, msg, sizeof(msg));
}

#endif