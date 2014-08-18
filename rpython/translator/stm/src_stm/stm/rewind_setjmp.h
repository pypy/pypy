/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _REWIND_SETJMP_H_
#define _REWIND_SETJMP_H_


#include <stddef.h>

/************************************************************
There is a singly-linked list of frames in each thread
rjthread->head->prev->prev->prev

Another singly-linked list is the list of copied stack-slices.
When doing a setjmp(), we copy the top-frame, free all old
stack-slices, and link it to the top-frame->moved_off.
When returning from the top-frame while moved_off still points
to a slice, we also need to copy the top-frame->prev frame/slice
and add it to this list (pointed to by moved_off).
--------------------------------------------------------------

           :                   :       ^^^^^
           |-------------------|    older frames in the stack
           |   prev=0          |
     ,---> | rewind_jmp_buf    |
     |     |-------------------|
     |     |                   |
     |     :                   :
     |     :                   :
     |     |                   |
     |     |-------------------|
     `---------prev            |
    ,----> | rewind_jmp_buf    |
    |      +-------------------|
    |      |                   |
    |      :                   :
    |      |                   |
    |      |-------------------|
    `----------prev            |
     ,---> | rewind_jmp_buf    | <--------------- MOVED_OFF_BASE
     |     |----------------  +-------------+
     |     |                  | STACK COPY  |
     |     |                  :             :
     |     :                  |  size       |
     |     |                  |  next       | <---- MOVED_OFF
     |     |                  +---|------  +-------------+
     |     |                   |  |        | STACK COPY  |
     |     |-------------------|  |        : (SEQUEL)    :
     `---------prev            |  |        :             :
HEAD-----> | rewind_jmp_buf    |  |        |             |
           |-------------------|  |        |  size       |
                                  `------> |  next=0     |
                                           +-------------+


************************************************************/

typedef struct _rewind_jmp_buf {
    char *shadowstack_base;
    struct _rewind_jmp_buf *prev;
    char *frame_base;
    /* NB: PyPy's JIT has got details of this structure hard-coded,
       as follows: it uses 2 words only (so frame_base is invalid)
       and sets the lowest bit of 'shadowstack_base' to tell this */
} rewind_jmp_buf;

typedef struct {
    rewind_jmp_buf *head;
    rewind_jmp_buf *initial_head;
    char *moved_off_base;
    char *moved_off_ssbase;
    struct _rewind_jmp_moved_s *moved_off;
    void *jmpbuf[5];
    long repeat_count;
} rewind_jmp_thread;


/* remember the current stack and ss_stack positions */
#define rewind_jmp_enterframe(rjthread, rjbuf, ss)   do {  \
    assert((((long)(ss)) & 1) == 0);                       \
    (rjbuf)->frame_base = __builtin_frame_address(0);      \
    (rjbuf)->shadowstack_base = (char *)(ss);              \
    (rjbuf)->prev = (rjthread)->head;                      \
    (rjthread)->head = (rjbuf);                            \
} while (0)

/* go up one frame. if there was a setjmp call in this frame,
 */
#define rewind_jmp_leaveframe(rjthread, rjbuf, ss)   do {    \
    assert((rjbuf)->shadowstack_base == (char *)(ss));       \
    (rjthread)->head = (rjbuf)->prev;                        \
    if ((rjbuf)->frame_base == (rjthread)->moved_off_base) { \
        assert((rjthread)->moved_off_ssbase == (char *)(ss));\
        _rewind_jmp_copy_stack_slice(rjthread);              \
    }                                                        \
} while (0)

long rewind_jmp_setjmp(rewind_jmp_thread *rjthread, void *ss);
void rewind_jmp_longjmp(rewind_jmp_thread *rjthread) __attribute__((noreturn));
char *rewind_jmp_restore_shadowstack(rewind_jmp_thread *rjthread);
char *rewind_jmp_enum_shadowstack(rewind_jmp_thread *rjthread,
                                  void *callback(void *, const void *, size_t));

#define rewind_jmp_forget(rjthread)  do {                               \
    if ((rjthread)->moved_off) _rewind_jmp_free_stack_slices(rjthread); \
    (rjthread)->moved_off_base = 0;                                     \
    (rjthread)->moved_off_ssbase = 0;                                   \
} while (0)

void _rewind_jmp_copy_stack_slice(rewind_jmp_thread *);
void _rewind_jmp_free_stack_slices(rewind_jmp_thread *);

#define rewind_jmp_armed(rjthread)   ((rjthread)->moved_off_base != 0)

#endif
