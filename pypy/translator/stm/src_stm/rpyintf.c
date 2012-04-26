/* -*- c-basic-offset: 2 -*- */

#include "src_stm/fifo.c"


/* this mutex is used to ensure non-conflicting accesses to global
   data in run_thread(). */
static pthread_mutex_t mutex_global = PTHREAD_MUTEX_INITIALIZER;

/* this lock is acquired if and only if there are no tasks pending,
   i.e. the fifo stm_g_pending is empty. */
static pthread_mutex_t mutex_no_tasks_pending = PTHREAD_MUTEX_INITIALIZER;

/* some global data put there by run_all_transactions(). */
static stm_fifo_t stm_g_pending;
static int stm_g_num_threads, stm_g_num_waiting_threads, stm_g_finished;


static void* perform_transaction(void *transaction)
{
  void *new_transaction_list;
  jmp_buf _jmpbuf;
  long counter;
  volatile long v_counter = 0;

  setjmp(_jmpbuf);

  begin_transaction(&_jmpbuf);

  counter = v_counter;
  v_counter = counter + 1;

  new_transaction_list = pypy_g__stm_run_transaction(transaction, counter);

  commit_transaction();

  return new_transaction_list;
}

static void add_list(void *new_transaction_list)
{
  bool_t was_empty;

  if (new_transaction_list == NULL)
    return;

  was_empty = fifo_is_empty(&stm_g_pending);
  fifo_extend(&stm_g_pending, new_transaction_list);
  if (was_empty)
    pthread_mutex_unlock(&mutex_no_tasks_pending);
}


/* the main function running a thread */
static void *run_thread(void *ignored)
{
  pthread_mutex_lock(&mutex_global);
  pypy_g__stm_thread_starting();

  while (1)
    {
      if (fifo_is_empty(&stm_g_pending))
        {
          stm_g_num_waiting_threads += 1;
          if (stm_g_num_waiting_threads == stm_g_num_threads)
            {
              stm_g_finished = 1;
              pthread_mutex_unlock(&mutex_no_tasks_pending);
            }
          pthread_mutex_unlock(&mutex_global);

          pthread_mutex_lock(&mutex_no_tasks_pending);
          pthread_mutex_unlock(&mutex_no_tasks_pending);

          pthread_mutex_lock(&mutex_global);
          stm_g_num_waiting_threads -= 1;
          if (stm_g_finished)
            break;
        }
      else
        {
          void *new_transaction_list;
          void *transaction = fifo_popleft(&stm_g_pending);
          if (fifo_is_empty(&stm_g_pending))
            pthread_mutex_lock(&mutex_no_tasks_pending);
          pthread_mutex_unlock(&mutex_global);

          while (1)
            {
              new_transaction_list = perform_transaction(transaction);

              /* for now, always break out of this loop,
                 unless 'new_transaction_list' contains precisely one item */
              if (new_transaction_list == NULL)
                break;
              if (fifo_next(new_transaction_list) != NULL)
                break;

              transaction = new_transaction_list;   /* single element */
            }

          pthread_mutex_lock(&mutex_global);
          add_list(new_transaction_list);
        }
    }

  pypy_g__stm_thread_stopping();
  pthread_mutex_unlock(&mutex_global);
  return NULL;
}

void stm_run_all_transactions(void *initial_transaction,
                              long num_threads)
{
  long i;
  pthread_t *th = malloc(num_threads * sizeof(pthread_t*));
  if (th == NULL)
    {
      /* XXX turn into a nice exception */
      fprintf(stderr, "out of memory: too many threads?\n");
      exit(1);
    }

  fifo_init(&stm_g_pending);
  fifo_append(&stm_g_pending, initial_transaction);
  stm_g_num_threads = (int)num_threads;
  stm_g_num_waiting_threads = 0;
  stm_g_finished = 0;

  for (i=0; i<num_threads; i++)
    {
      int status = pthread_create(&th[i], NULL, run_thread, NULL);
      if (status != 0)
        {
          /* XXX turn into a nice exception */
          fprintf(stderr, "fatal error: cannot create thread %ld/%ld\n",
                  i, num_threads);
          exit(1);
        }
    }

  for (i=0; i<num_threads; i++)
    {
      void *retval = NULL;
      int ret = pthread_join(th[i], &retval);
      if (ret != 0 || retval != NULL)
        {
          /* XXX? */
          fprintf(stderr, "warning: thread %ld/%ld exited with %d (%p)\n",
                  i, num_threads, ret, retval);
        }
    }
}
