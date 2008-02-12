/* custom checking allocators a la Electric Fence */
#include <stdlib.h>
#include <stdio.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#define PAGESIZE 4096
#ifndef MALLOC_BIGBUFFER
# define MALLOC_BIGBUFFER   (PAGESIZE*32768)   /* 128MB */
#endif


struct _alloc_s {
  void* ptr;
  int npages;
};
static void* _na_start = NULL;
static char* _na_cur;

static void _na_assert(int x, char* msg)
{
  if (!x)
    {
      fprintf(stderr, "linuxmemchk: failed assertion: %s\n", msg);
      abort();
    }
}

static struct _alloc_s* _na_find(void* data)
{
  int err;
  long data1;
  struct _alloc_s* s;
  _na_assert(_na_start+PAGESIZE <= data &&
             data < _na_start+MALLOC_BIGBUFFER-PAGESIZE,
             "corrupted na_start");
  data1 = (long) data;
  data1 &= ~(PAGESIZE-1);
  data1 -= PAGESIZE;
  err = mprotect((void*) data1, PAGESIZE, PROT_READ|PROT_WRITE);
  _na_assert(!err, "mprotect[1] failed");
  s = (struct _alloc_s*) data1;
  _na_assert(s->npages > 0, "corrupted s->npages");
  return s;
}

void* PyObject_Malloc(size_t size)
{
  int err, npages = (size + PAGESIZE-1) / PAGESIZE + 1;
  struct _alloc_s* s;
  char* data;
  if (_na_start == NULL)
    {
      _na_start = mmap(NULL, MALLOC_BIGBUFFER, PROT_NONE,
                       MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
      _na_assert(_na_start != MAP_FAILED, "initial mmap failed");
      _na_cur = (char*) _na_start;
    }
  s = (struct _alloc_s*) _na_cur;
  _na_cur += npages * PAGESIZE;
  if (_na_cur >= ((char*) _na_start) + MALLOC_BIGBUFFER)
    {
      fprintf(stderr, "linuxmemchk.c: Nothing wrong so far, but we are running out\nlinuxmemchk.c: of mmap'ed memory.  Increase MALLOC_BIGBUFFER.\n");
      abort();
    }
  err = mprotect(s, npages * PAGESIZE, PROT_READ|PROT_WRITE|PROT_EXEC);
  _na_assert(!err, "mprotect[2] failed");
  s->ptr = data = _na_cur - /*((size+3)&~3)*/ size;
  s->npages = npages;
  err = mprotect(s, PAGESIZE, PROT_NONE);
  _na_assert(!err, "mprotect[3] failed");
  return data;
}

void PyObject_Free(void* data)
{
  int err, npages;
  struct _alloc_s* s;
  if (data == NULL)
    return;
  s = _na_find(data);
  _na_assert(s->ptr == data, "free got a pointer not returned by malloc");
  npages = s->npages;
  s->npages = 0;
  err = mprotect(s, npages * PAGESIZE, PROT_NONE);
  _na_assert(!err, "mprotect[4] failed");
}

void* PyObject_Realloc(void* data, size_t nsize)
{
  size_t size;
  struct _alloc_s* s = _na_find(data);
  void* ndata = PyObject_Malloc(nsize);

  _na_assert(s->ptr == data, "realloc got a pointer not returned by malloc");
  size = ((char*)s) + s->npages * PAGESIZE - (char*)data;
  memcpy(ndata, data, size<nsize ? size : nsize);
  PyObject_Free(data);
  return ndata;
}
