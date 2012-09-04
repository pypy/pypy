
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
