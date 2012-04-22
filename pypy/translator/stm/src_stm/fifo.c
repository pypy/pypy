/* -*- c-basic-offset: 2 -*- */


/* xxx Direct access to this field.  Relies on genc producing always the
   same names, but that should be ok. */
#define NEXT(item)  (((struct pypy_pypy_rlib_rstm_Transaction0 *)(item)) \
                     ->t_inst__next_transaction)


typedef struct {
    void *first;
    void *last;
} stm_fifo_t;


static void fifo_init(stm_fifo_t *fifo)
{
  fifo->first = NULL;
  fifo->last = NULL;
}

static void *fifo_next(void *item)
{
  return NEXT(item);
}

static void fifo_append(stm_fifo_t *fifo, void *newitem)
{
  NEXT(newitem) = NULL;
  if (fifo->last == NULL)
    fifo->first = newitem;
  else
    NEXT(fifo->last) = newitem;
  fifo->last = newitem;
}

static bool_t fifo_is_empty(stm_fifo_t *fifo)
{
  assert((fifo->first == NULL) == (fifo->last == NULL));
  return (fifo->first == NULL);
}

static void *fifo_popleft(stm_fifo_t *fifo)
{
  void *item = fifo->first;
  fifo->first = NEXT(item);
  if (fifo->first == NULL)
    fifo->last = NULL;
  NEXT(item) = NULL;      /* ensure the NEXT is cleared,
                             to avoid spurious keepalives */
  return item;
}

static void fifo_extend(stm_fifo_t *fifo, void *newitems)
{
  if (fifo->last == NULL)
    fifo->first = newitems;
  else
    NEXT(fifo->last) = newitems;

  while (NEXT(newitems) != NULL)
    newitems = NEXT(newitems);

  fifo->last = newitems;
}

#undef NEXT
