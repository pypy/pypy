#include <stdlib.h>
#include <string.h>
#include "src/cjkcodecs/multibytecodec.h"
#include "src/cjkcodecs/fixnames.h"


/************************************************************/
/* codec registry                                           */

RPY_EXTERN struct pypy_cjk_module_s pypy_cjkmodule_cn;
RPY_EXTERN struct pypy_cjk_module_s pypy_cjkmodule_hk;
RPY_EXTERN struct pypy_cjk_module_s pypy_cjkmodule_iso2022;
RPY_EXTERN struct pypy_cjk_module_s pypy_cjkmodule_jp;
RPY_EXTERN struct pypy_cjk_module_s pypy_cjkmodule_kr;
RPY_EXTERN struct pypy_cjk_module_s pypy_cjkmodule_tw;

static struct pypy_cjk_module_s *const pypy_cjk_modules[] = {
  &pypy_cjkmodule_cn,
  &pypy_cjkmodule_hk,
  &pypy_cjkmodule_iso2022,
  &pypy_cjkmodule_jp,
  &pypy_cjkmodule_kr,
  &pypy_cjkmodule_tw,
  NULL
};

static void init_module(struct pypy_cjk_module_s *m)
{
  int i;
  if (m->initialized)
    return;
  m->add_mappings();
  m->add_codecs();
  for (i = 0; i < m->num_codecs; i++)
    m->codec_list[i].modstate = m->modstate;
  m->initialized = 1;
}

int pypy_cjk_importmap(const char *locale, const char *charset,
                       const void **encmap, const void **decmap)
{
  struct pypy_cjk_module_s *const *mp;
  for (mp = pypy_cjk_modules; *mp != NULL; mp++)
    {
      struct pypy_cjk_module_s *m = *mp;
      int i;
      if (strcmp(m->name, locale) != 0)
        continue;
      init_module(m);
      for (i = 0; i < m->num_mappings; i++)
        {
          const struct dbcs_map *map = &m->mapping_list[i];
          if (strcmp(map->charset, charset) == 0)
            {
              if (encmap != NULL)
                *encmap = map->encmap;
              if (decmap != NULL)
                *decmap = map->decmap;
              return 0;
            }
        }
    }
  return -1;
}

const MultibyteCodec *pypy_cjk_getcodec(const char *name)
{
  struct pypy_cjk_module_s *const *mp;
  for (mp = pypy_cjk_modules; *mp != NULL; mp++)
    {
      struct pypy_cjk_module_s *m = *mp;
      int i;
      init_module(m);
      for (i = 0; i < m->num_codecs; i++)
        {
          const MultibyteCodec *codec = &m->codec_list[i];
          if (strcmp(codec->encoding, name) == 0)
            {
              if (codec->codecinit != NULL && codec->codecinit(codec) != 0)
                return NULL;
              return codec;
            }
        }
    }
  return NULL;
}


/************************************************************/
/* decoding                                                 */

struct pypy_cjk_dec_s *pypy_cjk_dec_new(const MultibyteCodec *codec)
{
  struct pypy_cjk_dec_s *d = malloc(sizeof(struct pypy_cjk_dec_s));
  if (!d)
    return NULL;
  memset(&d->state, 0, sizeof(d->state));
  if (codec->decinit != NULL && codec->decinit(&d->state, codec) != 0)
    {
      free(d);
      return NULL;
    }
  d->codec = codec;
  d->outbuf_start = NULL;
  return d;
}

Py_ssize_t pypy_cjk_dec_init(struct pypy_cjk_dec_s *d,
                             char *inbuf, Py_ssize_t inlen)
{
  d->inbuf_start = (unsigned char *)inbuf;
  d->inbuf = (unsigned char *)inbuf;
  d->inbuf_end = (unsigned char *)inbuf + inlen;
  if (d->outbuf_start == NULL)
    {
      d->outbuf_start = (inlen <= (PY_SSIZE_T_MAX / sizeof(Py_UCS4)) ?
                         malloc(inlen * sizeof(Py_UCS4)) :
                         NULL);
      if (d->outbuf_start == NULL)
        return -1;
      d->outbuf_end = d->outbuf_start + inlen;
    }
  d->outbuf = d->outbuf_start;
  return 0;
}

void pypy_cjk_dec_free(struct pypy_cjk_dec_s *d)
{
  free(d->outbuf_start);
  free(d);
}

int pypy_cjk_dec_expand(struct pypy_cjk_dec_s *d, Py_ssize_t esize)
{
  Py_ssize_t orgpos, orgsize;
  Py_UCS4 *newbuf;

  orgpos = d->outbuf - d->outbuf_start;
  orgsize = d->outbuf_end - d->outbuf_start;
  esize = (esize < (orgsize >> 1) ? (orgsize >> 1) | 1 : esize);
  newbuf = (esize <= (PY_SSIZE_T_MAX / sizeof(Py_UCS4) - orgsize) ?
            realloc(d->outbuf_start, (orgsize + esize) * sizeof(Py_UCS4)) :
            NULL);
  if (!newbuf)
    return -1;
  d->outbuf_start = newbuf;
  d->outbuf = newbuf + orgpos;
  d->outbuf_end = newbuf + orgsize + esize;
  return 0;
}

Py_ssize_t pypy_cjk_dec_chunk(struct pypy_cjk_dec_s *d)
{
  while (1)
    {
      Py_ssize_t r;
      Py_ssize_t inleft = (Py_ssize_t)(d->inbuf_end - d->inbuf);
      if (inleft == 0)
        return 0;
      r = d->codec->decode(&d->state, d->codec, &d->inbuf, inleft, d);
      if (r != MBERR_TOOSMALL)
        return r;
      /* output buffer too small; grow it and continue. */
      if (pypy_cjk_dec_expand(d, -1) == -1)
        return MBERR_NOMEMORY;
    }
}

Py_UCS4 *pypy_cjk_dec_outbuf(struct pypy_cjk_dec_s *d)
{
  return d->outbuf_start;
}

Py_ssize_t pypy_cjk_dec_outlen(struct pypy_cjk_dec_s *d)
{
  return d->outbuf - d->outbuf_start;
}

Py_ssize_t pypy_cjk_dec_inbuf_remaining(struct pypy_cjk_dec_s *d)
{
  return d->inbuf_end - d->inbuf;
}

Py_ssize_t pypy_cjk_dec_inbuf_consumed(struct pypy_cjk_dec_s* d)
{
  return d->inbuf - d->inbuf_start;
}

Py_ssize_t pypy_cjk_dec_replace_on_error(struct pypy_cjk_dec_s* d,
                                         Py_UCS4 *newbuf, Py_ssize_t newlen,
                                         Py_ssize_t in_offset)
{
  if (newlen > 0)
    {
      if (d->outbuf + newlen > d->outbuf_end)
        if (pypy_cjk_dec_expand(d, newlen) == -1)
          return MBERR_NOMEMORY;
      memcpy(d->outbuf, newbuf, newlen * sizeof(Py_UCS4));
      d->outbuf += newlen;
    }
  d->inbuf = d->inbuf_start + in_offset;
  return 0;
}

/************************************************************/
/* encoding                                                 */

#define PYPY_CJK_UCS4_KIND 4   /* CPython's PyUnicode_4BYTE_KIND */

struct pypy_cjk_enc_s *pypy_cjk_enc_new(const MultibyteCodec *codec)
{
  struct pypy_cjk_enc_s *d = malloc(sizeof(struct pypy_cjk_enc_s));
  if (!d)
    return NULL;
  memset(&d->state, 0, sizeof(d->state));
  if (codec->encinit != NULL && codec->encinit(&d->state, codec) != 0)
    {
      free(d);
      return NULL;
    }
  d->codec = codec;
  d->outbuf_start = NULL;
  return d;
}

void pypy_cjk_enc_copystate(struct pypy_cjk_enc_s *dst, struct pypy_cjk_enc_s *src)
{
    dst->state = src->state;
}

Py_ssize_t pypy_cjk_enc_init(struct pypy_cjk_enc_s *d,
                             Py_UCS4 *inbuf, Py_ssize_t inlen)
{
  Py_ssize_t outlen;
  d->inbuf_start = inbuf;
  d->inpos = 0;
  d->inlen = inlen;
  if (d->outbuf_start == NULL)
    {
      if (inlen > (PY_SSIZE_T_MAX - 16) / 2)
        return -1;
      outlen = inlen * 2 + 16;
      d->outbuf_start = malloc(outlen);
      if (d->outbuf_start == NULL)
        return -1;
      d->outbuf_end = d->outbuf_start + outlen;
    }
  d->outbuf = d->outbuf_start;
  return 0;
}

void pypy_cjk_enc_free(struct pypy_cjk_enc_s *d)
{
  free(d->outbuf_start);
  free(d);
}

static int expand_encodebuffer(struct pypy_cjk_enc_s *d, Py_ssize_t esize)
{
  Py_ssize_t orgpos, orgsize;
  unsigned char *newbuf;

  orgpos = d->outbuf - d->outbuf_start;
  orgsize = d->outbuf_end - d->outbuf_start;
  esize = (esize < (orgsize >> 1) ? (orgsize >> 1) | 1 : esize);
  newbuf = (esize <= PY_SSIZE_T_MAX - orgsize ?
            realloc(d->outbuf_start, orgsize + esize) :
            NULL);
  if (!newbuf)
    return -1;
  d->outbuf_start = newbuf;
  d->outbuf = newbuf + orgpos;
  d->outbuf_end = newbuf + orgsize + esize;
  return 0;
}

Py_ssize_t pypy_cjk_enc_chunk(struct pypy_cjk_enc_s *d, Py_ssize_t flags)
{
  while (1)
    {
      Py_ssize_t r;
      Py_ssize_t inleft = d->inlen - d->inpos;
      Py_ssize_t outleft = (Py_ssize_t)(d->outbuf_end - d->outbuf);
      if (inleft == 0 && !(flags & MBENC_RESET))
        return 0;
      r = d->codec->encode(&d->state, d->codec,
                           PYPY_CJK_UCS4_KIND, d->inbuf_start,
                           &d->inpos, d->inlen,
                           &d->outbuf, outleft, (int)flags);
      if (r != MBERR_TOOSMALL)
        return r;
      /* output buffer too small; grow it and continue. */
      if (expand_encodebuffer(d, -1) == -1)
        return MBERR_NOMEMORY;
    }
}

Py_ssize_t pypy_cjk_enc_reset(struct pypy_cjk_enc_s *d)
{
  if (d->codec->encreset == NULL)
    return 0;

  while (1)
    {
      Py_ssize_t r;
      Py_ssize_t outleft = (Py_ssize_t)(d->outbuf_end - d->outbuf);
      r = d->codec->encreset(&d->state, d->codec, &d->outbuf, outleft);
      if (r != MBERR_TOOSMALL)
        return r;
      /* output buffer too small; grow it and continue. */
      if (expand_encodebuffer(d, -1) == -1)
        return MBERR_NOMEMORY;
    }
}

char *pypy_cjk_enc_outbuf(struct pypy_cjk_enc_s *d)
{
  return (char *)d->outbuf_start;
}

Py_ssize_t pypy_cjk_enc_outlen(struct pypy_cjk_enc_s *d)
{
  return d->outbuf - d->outbuf_start;
}

Py_ssize_t pypy_cjk_enc_inbuf_remaining(struct pypy_cjk_enc_s *d)
{
  return d->inlen - d->inpos;
}

Py_ssize_t pypy_cjk_enc_inbuf_consumed(struct pypy_cjk_enc_s* d)
{
  return d->inpos;
}

Py_ssize_t pypy_cjk_enc_replace_on_error(struct pypy_cjk_enc_s* d,
                                         char *newbuf, Py_ssize_t newlen,
                                         Py_ssize_t in_offset)
{
  if (newlen > 0)
    {
      if (d->outbuf + newlen > d->outbuf_end)
        if (expand_encodebuffer(d, newlen) == -1)
          return MBERR_NOMEMORY;
      memcpy(d->outbuf, newbuf, newlen);
      d->outbuf += newlen;
    }
  d->inpos = in_offset;
  return 0;
}

const MultibyteCodec *pypy_cjk_enc_getcodec(struct pypy_cjk_enc_s *d)
{
  return d->codec;
}
