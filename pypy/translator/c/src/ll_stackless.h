
#ifdef USE_STACKLESS

#ifndef PYPY_STANDALONE
#  error "Stackless support: only for stand-alone executables"
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

slp_frame_t* slp_frame_stack_top = NULL;
slp_frame_t* slp_frame_stack_bottom = NULL;
int slp_restart_substate;
long slp_retval_long;
void *slp_retval_ptr;
slp_frame_t* slp_new_frame(int size, int state);


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

	  case -1:
		  slp_retval_long = ((long(*)(void)) fn) ();
		  break;

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

slp_frame_t* slp_new_frame(int size, int state)
{
  slp_frame_t* f = (slp_frame_t*) malloc(size);
  f->f_back = NULL;
  f->state = state;
  return f;
}

int slp_standalone_entry_point(RPyListOfString *argv)
{
	int result = PYPY_STANDALONE(argv);
	if (slp_frame_stack_bottom) {
		slp_main_loop();
		result = (int) slp_retval_long;
	}
	return result;
}


/* example function for testing */

long LL_stackless_stack_frames_depth(void)
{
	if (slp_frame_stack_top) goto resume;

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


struct slp_state_decoding_entry_s slp_state_decoding_table[] = {
	{ LL_stackless_stack_frames_depth, -1 },    /* 0 */
	/* XXX WARNING FOR NOW MAKE SURE StacklessData.globalstatecounter
	   counts the number of manually-inserted lines above !!!!!!!!!! */
#include "slp_state_decoding.h"
};

#include "slp_defs.h"

#endif USE_STACKLESS
