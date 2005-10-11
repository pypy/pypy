
#ifdef USE_STACKLESS

#ifndef PYPY_STANDALONE
#  error "Stackless support: only for stand-alone executables"
#endif

#ifndef MAX_STACK_SIZE
#define MAX_STACK_SIZE (1 << 20)
#endif

#define STANDALONE_ENTRY_POINT   slp_standalone_entry_point


typedef struct slp_frame_s {
  struct slp_frame_s *f_back;
  int state;
} slp_frame_t;

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
extern char *slp_base_stack_pointer;

slp_frame_t* slp_new_frame(int size, int state);
long LL_stackless_stack_frames_depth(void);
void slp_main_loop(void);
char LL_stackless_stack_too_big(void);

#ifndef PYPY_NOT_MAIN_FILE

/* implementations */

slp_frame_t* slp_frame_stack_top = NULL;
slp_frame_t* slp_frame_stack_bottom = NULL;
int slp_restart_substate;
long slp_retval_long;
double slp_retval_double;
void *slp_retval_voidptr;
char *slp_base_stack_pointer = NULL;

slp_frame_t* slp_new_frame(int size, int state)
{
  slp_frame_t* f = (slp_frame_t*) malloc(size);
  assert(f != NULL);   /* XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX */
  f->f_back = NULL;
  f->state = state;
  return f;
}


/* example function for testing */

long LL_stackless_stack_frames_depth(void)
{
	if (slp_frame_stack_top)
	    goto resume;

	slp_frame_stack_top = slp_frame_stack_bottom =
		slp_new_frame(sizeof(slp_frame_t), 0);
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

void LL_stackless_stack_unwind(void)
{
    if (slp_frame_stack_top)
        goto resume;

    slp_frame_stack_top = slp_frame_stack_bottom =
        slp_new_frame(sizeof(slp_frame_t), 0);
    return ;

 resume:
    slp_frame_stack_top = NULL;
}

char LL_stackless_stack_too_big(void)
{
  char local;
  long result;
  /* compute the difference between local variable and
   * and a stack origin pointer
   */
  result = &local - slp_base_stack_pointer;
  if (-MAX_STACK_SIZE < result && result < MAX_STACK_SIZE){
    return 0;
  }
  return 1;
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

          free(pending);  /* consumed by the previous call */
          if (slp_frame_stack_bottom)
            break;
          if (!back)
            return;
          pending = back;
          slp_frame_stack_top = pending;
        }
      assert(slp_frame_stack_bottom->f_back == NULL);
      slp_frame_stack_bottom->f_back = back;
    }
}

int slp_standalone_entry_point(RPyListOfString *argv)
{
	char local;
	int result;
	slp_base_stack_pointer = &local;
	result = PYPY_STANDALONE(argv);
	if (slp_frame_stack_bottom) {
		slp_main_loop();
		result = (int) slp_retval_long;
	}
	return result;
}

#endif /* PYPY_NOT_MAIN_FILE */

#endif USE_STACKLESS

