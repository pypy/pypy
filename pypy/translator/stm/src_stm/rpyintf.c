/* -*- c-basic-offset: 2 -*- */

long stm_thread_id(void)
{
  struct tx_descriptor *d = thread_descriptor;
  if (d == NULL)
    return 0;    /* no thread_descriptor yet, assume it's the main thread */
  return d->my_lock_word;
}

void stm_set_tls(void *newtls, long in_main_thread)
{
  struct tx_descriptor *d = descriptor_init(in_main_thread);
  d->rpython_tls_object = newtls;
}

void *stm_get_tls(void)
{
  return thread_descriptor->rpython_tls_object;
}

void stm_del_tls(void)
{
  descriptor_done();
}

void *stm_tldict_lookup(void *key)
{
  struct tx_descriptor *d = thread_descriptor;
  wlog_t* found;
  REDOLOG_FIND(d->redolog, key, found, goto not_found);
  return found->val;

 not_found:
  return NULL;
}

void stm_tldict_add(void *key, void *value)
{
  struct tx_descriptor *d = active_thread_descriptor;
  assert(d != NULL);
  redolog_insert(&d->redolog, key, value);
}

void stm_tldict_enum(void(*callback)(void*, void*, void*))
{
  struct tx_descriptor *d = thread_descriptor;
  wlog_t *item;
  void *tls = stm_get_tls();

  REDOLOG_LOOP_FORWARD(d->redolog, item)
    {
      callback(tls, item->addr, item->val);
    } REDOLOG_LOOP_END;
}

void stm_setup_size_getter(long(*getsize_fn)(void*))
{
  rpython_get_size = getsize_fn;
}

long stm_in_transaction(void)
{
  struct tx_descriptor *d = thread_descriptor;
  return d != NULL;
}

void _stm_activate_transaction(long activate)
{
  assert(thread_descriptor != NULL);
  if (activate)
    {
      active_thread_descriptor = thread_descriptor;
    }
  else
    {
      active_thread_descriptor = NULL;
    }
}


/* a helper to directly read the field '_next_transaction' on
   RPython instances of pypy.rlib.rstm.Transaction */
static void *next_transaction(void *



/* this lock is acquired when we start running transactions, and
   released only when we are finished. */
static pthread_mutex_t mutex_unfinished = PTHREAD_MUTEX_INITIALIZER;

/* this mutex is used to ensure non-conflicting accesses to global
   data in run_thread(). */
static pthread_mutex_t mutex_global = PTHREAD_MUTEX_INITIALIZER;

/* some global data put there by run_all_transactions(). */
typedef void *(*run_transaction_t)(void *, long);
static run_transaction_t g_run_transaction;
static void *g_first_transaction, *g_last_transaction;
static int g_num_threads;
static int g_num_waiting_threads;

/* the main function running a thread */
static void *run_thread(void *ignored)
{
  pthread_mutex_lock(&mutex_global);

  g_num_waiting_threads++;
  if (g_num_waiting_threads == g_num_threads)
    pthread_mutex_unlock(&mutex_unfinished);

  pthread_mutex_unlock(&mutex_global);
  return NULL;
}

void stm_run_all_transactions(run_transaction_t run_transaction,
                              void *initial_transaction,
                              long num_threads)
{
  int i;
  g_run_transaction = run_transaction;
  g_first_transaction = initial_transaction;
  g_last_transaction = initial_transaction;
  g_num_threads = (int)num_threads;
  g_num_waiting_threads = 0;

  pthread_mutex_lock(&mutex_unfinished);

  for (i=0; i<(int)num_threads; i++)
    {
      pthread_t th;
      int status = pthread_create(&th, NULL, run_thread, NULL);
      assert(status == 0);
      pthread_detach(th);
    }

  pthread_mutex_lock(&mutex_unfinished);
  pthread_mutex_unlock(&mutex_unfinished);
}
