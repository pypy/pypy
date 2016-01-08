
#define VMPROF_CODE_TAG 1
#define VMPROF_BLACKHOLE_TAG 2
#define VMPROF_JITTED_TAG 3
#define VMPROF_JITTING_TAG 4
#define VMPROF_GC_TAG 5
// whatever we want here

typedef struct vmprof_stack {
    struct vmprof_stack* next;
    long value;
    long kind;
} vmprof_stack;

// the kind is WORD so we consume exactly 3 WORDs and we don't have
// to worry too much. There is a potential for squeezing it with bit
// patterns into one WORD, but I don't want to care RIGHT NOW, potential
// for future optimization potential

RPY_EXTERN vmprof_stack* vmprof_global_stack;

RPY_EXTERN void *vmprof_address_of_global_stack(void)
{
    return (void*)&vmprof_global_stack;
}
