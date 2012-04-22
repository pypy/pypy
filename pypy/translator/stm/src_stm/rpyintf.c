/* -*- c-basic-offset: 2 -*- */

#include "src_stm/fifo.c"


/* this lock is acquired when we start running transactions, and
   released only when we are finished. */
static pthread_mutex_t mutex_unfinished = PTHREAD_MUTEX_INITIALIZER;

/* this mutex is used to ensure non-conflicting accesses to global
   data in run_thread(). */
static pthread_mutex_t mutex_global = PTHREAD_MUTEX_INITIALIZER;

/* this lock is acquired if and only if there are no tasks pending,
   i.e. the linked list stm_g_first_transaction ... stm_g_last_transaction is
   empty and both pointers are NULL. */
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
  if (stm_g_num_waiting_threads == 0)   /* only the last thread to leave */
    pthread_mutex_unlock(&mutex_unfinished);
  pthread_mutex_unlock(&mutex_global);
  return NULL;
}

void stm_run_all_transactions(void *initial_transaction,
                              long num_threads)
{
  int i;
  fifo_init(&stm_g_pending);
  fifo_append(&stm_g_pending, initial_transaction);
  stm_g_num_threads = (int)num_threads;
  stm_g_num_waiting_threads = 0;
  stm_g_finished = 0;

  pthread_mutex_lock(&mutex_unfinished);

  for (i=0; i<(int)num_threads; i++)
    {
      pthread_t th;
      int status = pthread_create(&th, NULL, run_thread, NULL);
      if (status != 0)
        {
          /* XXX turn into a nice exception */
          fprintf(stderr, "fatal error: cannot create threads\n");
          exit(1);
        }
      pthread_detach(th);
    }

  pthread_mutex_lock(&mutex_unfinished);
  pthread_mutex_unlock(&mutex_unfinished);
}
