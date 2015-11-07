
typedef struct vmprof_stack {
    struct vmprof_stack* next;
    long value;
} vmprof_stack;

extern vmprof_stack* vmprof_global_stack;