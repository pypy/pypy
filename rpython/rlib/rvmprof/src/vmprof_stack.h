
#define STACK_SIZE 8192
#include <stdlib.h>

typedef struct vmprof_stack {
    volatile long stack_depth;
    long stack_items[STACK_SIZE];
} vmprof_stack;

RPY_EXTERN void *vmprof_stack_new(void)
{
    vmprof_stack* stack = (vmprof_stack *)malloc(sizeof(vmprof_stack));
    stack->stack_depth = 0;
    return (void*)stack;
}

RPY_EXTERN int vmprof_stack_append(void *_stack, long item)
{
    vmprof_stack* stack = (vmprof_stack*)_stack;
    if (stack->stack_depth >= STACK_SIZE - 1)
        return -1;
    stack->stack_items[stack->stack_depth] = item;
    stack->stack_depth += 1;
    return 0;
}

RPY_EXTERN long vmprof_stack_pop(void *_stack)
{
    vmprof_stack* stack = (vmprof_stack*)_stack;
    long res;

    if (stack->stack_depth <= 0)
        return -1;
    res = stack->stack_items[stack->stack_depth];
    stack->stack_depth -= 1;
    return res;
}

RPY_EXTERN void vmprof_stack_free(void* stack)
{
    free(stack);
}