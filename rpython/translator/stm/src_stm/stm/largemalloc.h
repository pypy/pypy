/* Imported by rpython/translator/stm/import_stmgc.py */

/* all addresses passed to this interface should be "char *" pointers
   in the segment 0. */
void _stm_largemalloc_init_arena(char *data_start, size_t data_size);
int _stm_largemalloc_resize_arena(size_t new_size);
char *_stm_largemalloc_data_start(void);

/* large_malloc() and large_free() are not thread-safe.  This is
   due to the fact that they should be mostly called during minor or
   major collections, which have their own synchronization mecanisms. */
char *_stm_large_malloc(size_t request_size);
void _stm_large_free(char *data);
void _stm_largemalloc_sweep(void);

void _stm_large_dump(void);


#define LARGE_MALLOC_OVERHEAD   (2 * sizeof(size_t))   /* estimate */
