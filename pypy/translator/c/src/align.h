
#ifndef _PYPY_ALIGN_H
#define _PYPY_ALIGN_H

/* alignment for arena-based garbage collectors: the following line
   enforces an alignment that should be enough for any structure
   containing pointers and 'double' fields. */
struct rpy_memory_alignment_test1 {
  double d;
  void* p;
};
struct rpy_memory_alignment_test2 {
  char c;
  struct rpy_memory_alignment_test1 s;
};
#define MEMORY_ALIGNMENT	offsetof(struct rpy_memory_alignment_test2, s)
#define ROUND_UP_FOR_ALLOCATION(x, minsize)  \
  ((((x)>=(minsize)?(x):(minsize))           \
               + (MEMORY_ALIGNMENT-1)) & ~(MEMORY_ALIGNMENT-1))

#endif //_PYPY_ALIGN_H
