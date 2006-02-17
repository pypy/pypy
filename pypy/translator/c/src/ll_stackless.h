
#ifdef USE_STACKLESS

#ifndef PYPY_STANDALONE
#  error "Stackless support: only for stand-alone executables"
#endif

#define STANDALONE_ENTRY_POINT   slp_standalone_entry_point

#ifdef USING_BOEHM_GC
#define slp_malloc GC_MALLOC
#define slp_free(p)
#else
#define slp_malloc malloc
#define slp_free(p)free(p)
#endif


typedef struct slp_frame_s {
  struct slp_frame_s *f_back;
  int state;
} slp_frame_t;

typedef struct {
  slp_frame_t header;
  void* p0;
} slp_frame_1ptr_t;

struct slp_state_decoding_entry_s {
  void *function;
  int signature;
};

#include "slp_defs.h"

/* prototypes */

extern slp_frame_t* slp_frame_stack_top;
extern slp_frame_t* slp_frame_stack_bottom;
extern int slp_restart_substate;
extern long slp_retval_long;
extern double slp_retval_double;
extern void *slp_retval_voidptr;

slp_frame_t* slp_new_frame(int size, int state);
long LL_stackless_stack_frames_depth(void);
void slp_main_loop(void);
char LL_stackless_stack_too_big(void);
struct RPyOpaque_frame_stack_top *slp_return_current_frame_to_caller(void);
struct RPyOpaque_frame_stack_top *
LL_stackless_switch(struct RPyOpaque_frame_stack_top *c);

#ifndef PYPY_NOT_MAIN_FILE

/* implementations */

slp_frame_t* slp_frame_stack_top = NULL;
slp_frame_t* slp_frame_stack_bottom = NULL;
int slp_restart_substate;
long slp_retval_long;
double slp_retval_double;
void *slp_retval_voidptr;

slp_frame_t* slp_new_frame(int size, int state)
{
  slp_frame_t* f = (slp_frame_t*) slp_malloc(size);
  assert(f != NULL);   /* XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX */
  f->f_back = NULL;
  f->state = state;
  return f;
}

void LL_stackless_stack_unwind(void)
{
    if (slp_frame_stack_top)
        goto resume;

    slp_frame_stack_top = slp_frame_stack_bottom =
        slp_new_frame(sizeof(slp_frame_t), 0);
    RPyRaisePseudoException();
    return ;

 resume:
    slp_frame_stack_top = NULL;
}

struct RPyOpaque_frame_stack_top *slp_return_current_frame_to_caller(void)
{
  slp_frame_t *result = slp_frame_stack_top;
  assert(slp_frame_stack_top != NULL);
  assert(slp_frame_stack_bottom != NULL);
  slp_frame_stack_bottom->f_back = slp_new_frame(sizeof(slp_frame_t), 3);
  slp_frame_stack_top = slp_frame_stack_bottom = NULL;  /* stop unwinding */
  RPyExceptionClear();
  return (struct RPyOpaque_frame_stack_top *) result;
}

struct RPyOpaque_frame_stack_top *slp_end_of_yielding_function(void)
{
  assert(slp_frame_stack_top != NULL); /* can only be resumed from
                                       slp_return_current_frame_to_caller() */
  assert(slp_retval_voidptr != NULL);
  slp_frame_stack_top = (slp_frame_t *) slp_retval_voidptr;
  return NULL;
}

struct RPyOpaque_frame_stack_top *
LL_stackless_switch(struct RPyOpaque_frame_stack_top *c)
{
	slp_frame_t *f;
	slp_frame_t *result;
	if (slp_frame_stack_top)
		goto resume;

	/* first, unwind the current stack */
	f = slp_new_frame(sizeof(slp_frame_1ptr_t), 2);
	((slp_frame_1ptr_t *) f)->p0 = c;
	slp_frame_stack_top = slp_frame_stack_bottom = f;
        RPyRaisePseudoException();
	return NULL;

   resume:
	/* ready to do the switch.  The current (old) frame_stack_top is
	   f->f_back, which we store where it will be found immediately
	   after the switch */
	f = slp_frame_stack_top;
	result = f->f_back;

	/* grab the saved value of 'c' and do the switch */
	slp_frame_stack_top = (slp_frame_t *) (((slp_frame_1ptr_t *) f)->p0);
	return (struct RPyOpaque_frame_stack_top *) result;
}


/* example function for testing */

long LL_stackless_stack_frames_depth(void)
{
	if (slp_frame_stack_top)
	    goto resume;

	slp_frame_stack_top = slp_frame_stack_bottom =
		slp_new_frame(sizeof(slp_frame_t), 1);
        RPyRaisePseudoException();
	return -1;

 resume:
    {
	slp_frame_t* f = slp_frame_stack_top;
	int result;
	slp_frame_stack_top = NULL;

	result = 0;
	while (f) {
		result++;
		f = f->f_back;
	}
	return result;
    }
}

#include "slp_state_decoding.h"

void slp_main_loop(void)
{
  int state, signature;
  slp_frame_t* pending;
  slp_frame_t* back;
  void* fn;

  while (1)
    {
      slp_frame_stack_bottom = NULL;
      RPyExceptionClear();
      pending = slp_frame_stack_top;

      while (1)
        {
          back = pending->f_back;
          state = pending->state;
          fn = slp_state_decoding_table[state].function;
          signature = slp_state_decoding_table[state].signature;
          if (fn != NULL)
            slp_restart_substate = 0;
          else
            {
              slp_restart_substate = signature;
              state -= signature;
              fn = slp_state_decoding_table[state].function;
              signature = slp_state_decoding_table[state].signature;
            }

          switch (signature) {

#include "slp_signatures.h"

	  }

          slp_free(pending);  /* consumed by the previous call */
          if (slp_frame_stack_top)
            break;
          if (!back)
            return;
          pending = back;
          slp_frame_stack_top = pending;
        }
      /* slp_frame_stack_bottom is usually non-NULL here, apart from
         when returning from switch() */
      if (slp_frame_stack_bottom != NULL)
        {
          assert(slp_frame_stack_bottom->f_back == NULL);
          slp_frame_stack_bottom->f_back = back;
        }
    }
}

int slp_standalone_entry_point(RPyListOfString *argv)
{
	int result;
	result = PYPY_STANDALONE(argv);
	if (slp_frame_stack_bottom) {
		slp_main_loop();
		result = (int) slp_retval_long;
	}
	return result;
}

#endif /* PYPY_NOT_MAIN_FILE */

#endif /* USE_STACKLESS */

