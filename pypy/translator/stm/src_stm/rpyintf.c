
static __thread void *rpython_tls_object;

void stm_set_tls(void *newtls)
{
  rpython_tls_object = newtls;
}

void *stm_get_tls(void)
{
  return rpython_tls_object;
}

void stm_del_tls(void)
{
  rpython_tls_object = NULL;
}

gcptr stm_tldict_lookup(gcptr key)
{
  struct tx_descriptor *d = thread_descriptor;
  wlog_t* found;
  G2L_FIND(d->global_to_local, key, found, goto not_found);
  return found->val;

 not_found:
  return NULL;
}

void stm_tldict_add(gcptr key, gcptr value)
{
  struct tx_descriptor *d = thread_descriptor;
  assert(d != NULL);
  g2l_insert(&d->global_to_local, key, value);
}

void stm_tldict_enum(void)
{
  struct tx_descriptor *d = thread_descriptor;
  wlog_t *item;
  void *tls = stm_get_tls();
  struct gcroot_s *gcroots = FindRootsForLocalCollect();

  while (gcroots->R != NULL)
    {
      pypy_g__stm_enum_callback(tls, gcroots->R, gcroots->L);
      gcroots++;
    }
}

long stm_in_transaction(void)
{
  struct tx_descriptor *d = thread_descriptor;
  return d->active;
}

long stm_is_inevitable(void)
{
  struct tx_descriptor *d = thread_descriptor;
  return is_inevitable(d);
}

static long stm_regular_length_limit = LONG_MAX;

void stm_add_atomic(long delta)
{
  struct tx_descriptor *d = thread_descriptor;
  d->atomic += delta;
  update_reads_size_limit(d);
}

long stm_get_atomic(void)
{
  struct tx_descriptor *d = thread_descriptor;
  return d->atomic;
}

long stm_should_break_transaction(void)
{
  struct tx_descriptor *d = thread_descriptor;

  /* a single comparison to handle all cases:

     - if d->atomic, then we should return False.  This is done by
       forcing reads_size_limit to LONG_MAX as soon as atomic > 0.

     - otherwise, if is_inevitable(), then we should return True.
       This is done by forcing both reads_size_limit and
       reads_size_limit_nonatomic to 0 in that case.

     - finally, the default case: return True if
       d->list_of_read_objects.size is
       greater than reads_size_limit == reads_size_limit_nonatomic.
  */
#ifdef RPY_STM_ASSERT
  /* reads_size_limit is LONG_MAX if d->atomic, or else it is equal to
     reads_size_limit_nonatomic. */
  assert(d->reads_size_limit == (d->atomic ? LONG_MAX :
                                     d->reads_size_limit_nonatomic));
  /* if is_inevitable(), reads_size_limit_nonatomic should be 0
     (and thus reads_size_limit too, if !d->atomic.) */
  if (is_inevitable(d))
    assert(d->reads_size_limit_nonatomic == 0);
#endif

  return d->list_of_read_objects.size >= d->reads_size_limit;
}

void stm_set_transaction_length(long length_max)
{
  struct tx_descriptor *d = thread_descriptor;
  BecomeInevitable("set_transaction_length");
  stm_regular_length_limit = length_max;
}

#define END_MARKER   ((void*)-8)   /* keep in sync with stmframework.py */

void stm_perform_transaction(long(*callback)(void*, long), void *arg,
                             void *save_and_restore)
{
  jmp_buf _jmpbuf;
  long volatile v_counter = 0;
  void **volatile v_saved_value;
  long volatile v_atomic = thread_descriptor->atomic;
  assert((!thread_descriptor->active) == (!v_atomic));
  v_saved_value = *(void***)save_and_restore;
  /***/
  setjmp(_jmpbuf);
  /* After setjmp(), the local variables v_* are preserved because they
   * are volatile.  The other variables are only declared here. */
  struct tx_descriptor *d = thread_descriptor;
  long counter, result;
  void **restore_value;
  counter = v_counter;
  d->atomic = v_atomic;
  restore_value = v_saved_value;
  if (!d->atomic)
    {
      /* In non-atomic mode, we are now between two transactions.
         It means that in the next transaction's collections we know
         that we won't need to access the shadows stack beyond its
         current position.  So we add an end marker. */
      *restore_value++ = END_MARKER;
    }
  *(void***)save_and_restore = restore_value;

  do
    {
      v_counter = counter + 1;
      /* initialize 'reads_size_limit_nonatomic' from the configured
         length limit, scaled down by a factor of 2 for each time we
         retry an aborted transaction.  Note that as soon as such a
         shortened transaction succeeds, the next one will again have
         full length, for now. */
      d->reads_size_limit_nonatomic = stm_regular_length_limit >> counter;
      if (!d->atomic)
        BeginTransaction(&_jmpbuf);

      /* invoke the callback in the new transaction */
      result = callback(arg, counter);

      v_atomic = d->atomic;
      if (!d->atomic)
        CommitTransaction();
      counter = 0;
    }
  while (result == 1);  /* also stops if we got an RPython exception */

  if (d->atomic && d->setjmp_buf == &_jmpbuf)
    BecomeInevitable("perform_transaction left with atomic");

  *(void***)save_and_restore = v_saved_value;
}

void stm_abort_and_retry(void)
{
  AbortTransaction(4);    /* manual abort */
}
