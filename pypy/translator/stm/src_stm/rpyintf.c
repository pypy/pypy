/* -*- c-basic-offset: 2 -*- */

long stm_thread_id(void)
{
  struct tx_descriptor *d = thread_descriptor;
  if (d == NULL)
    return 0;    /* no thread_descriptor: it's the main thread */
  return d->my_lock_word;
}

static __thread void *rpython_tls_object;

void stm_set_tls(void *newtls, long in_main_thread)
{
  descriptor_init(in_main_thread);
  rpython_tls_object = newtls;
}

void *stm_get_tls(void)
{
  return rpython_tls_object;
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
  struct tx_descriptor *d = thread_descriptor;
  assert(d != NULL);
  redolog_insert(&d->redolog, key, value);
}

void stm_tldict_enum(void)
{
  struct tx_descriptor *d = thread_descriptor;
  wlog_t *item;
  void *tls = stm_get_tls();

  REDOLOG_LOOP_FORWARD(d->redolog, item)
    {
      pypy_g__stm_enum_callback(tls, item->addr, item->val);
    } REDOLOG_LOOP_END;
}

long stm_in_transaction(void)
{
  struct tx_descriptor *d = thread_descriptor;
  return d != NULL;
}

/************************************************************/

/* this lock is acquired when we start running transactions, and
   released only when we are finished. */
static pthread_mutex_t mutex_unfinished = PTHREAD_MUTEX_INITIALIZER;

/* this mutex is used to ensure non-conflicting accesses to global
   data in run_thread(). */
static pthread_mutex_t mutex_global = PTHREAD_MUTEX_INITIALIZER;

/* some global data put there by run_all_transactions(). */
static void *g_first_transaction, *g_last_transaction;
static int g_num_threads, g_num_waiting_threads;

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

void stm_run_all_transactions(void *initial_transaction,
                              long num_threads)
{
  int i;
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
