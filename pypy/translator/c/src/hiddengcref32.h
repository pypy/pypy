
/******************** 64-bit hiddengcref32 support ********************/

typedef unsigned int hiddengcref32_t;


void RPyPointerTooBig(void);

#ifndef PYPY_NOT_MAIN_FILE
void RPyPointerTooBig(void) {
  fprintf(stderr, "Fatal error: Pointer too big or misaligned.  "
                  "This can occur if your C\n"
                  "compiler puts static data after the first 32GB "
                  "of virtual address space.\n");
  abort();
}
#endif


#define SHOW_FROM_PTR32(x)   ((void*)(((unsigned long)(x)) << 3))
#define HIDE_INTO_PTR32(x)   ((hiddengcref32_t)(((unsigned long)(x)) >> 3))


#define OP_SHOW_FROM_PTR32(x, r)  r = SHOW_FROM_PTR32(x)

#define OP_HIDE_INTO_PTR32_CHECK(x, r)  \
   r = HIDE_INTO_PTR32(x); \
   if ((void*)(((unsigned long)(r)) << 3) != (x)) \
     RPyPointerTooBig()

#define OP_HIDE_INTO_PTR32(x, r)  \
   RPyAssert(!(((long)(x)) & ~0x7FFFFFFF8), "Pointer too big or misaligned"); \
   r = HIDE_INTO_PTR32(x)
