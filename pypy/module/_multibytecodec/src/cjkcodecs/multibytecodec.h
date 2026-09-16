
#ifndef _PYPY_MULTIBYTECODEC_H_
#define _PYPY_MULTIBYTECODEC_H_

#include "src/precommondefs.h"


#include <stddef.h>
#include <assert.h>

#ifdef _WIN64
typedef __int64 pypymbc_ssize_t;
#elif defined(_WIN32)
typedef int pypymbc_ssize_t;
#else
#include <unistd.h>
typedef ssize_t pypymbc_ssize_t;
#endif

#ifdef _WIN32
typedef unsigned int pypymbc_ucs4_t;
typedef unsigned short pypymbc_ucs2_t;
#else
#include <stdint.h>
typedef uint32_t pypymbc_ucs4_t;
typedef uint16_t pypymbc_ucs2_t;
#endif


/* The declarations below mirror CPython's Modules/cjkcodecs/multibytecodec.h
   so that the _codecs_*.c files can be verbatim copies of CPython's.
   The decoders write into a 'struct pypy_cjk_dec_s', which plays the role
   of CPython's _PyUnicodeWriter. */

typedef struct {
    unsigned char c[8];
} MultibyteCodec_State;

struct _cjk_mod_state;
struct _multibyte_codec;
struct pypy_cjk_dec_s;

typedef int (*mbcodec_init)(const struct _multibyte_codec *codec);
typedef pypymbc_ssize_t (*mbencode_func)(MultibyteCodec_State *state,
                        const struct _multibyte_codec *codec,
                        int kind, const void *data,
                        pypymbc_ssize_t *inpos, pypymbc_ssize_t inlen,
                        unsigned char **outbuf, pypymbc_ssize_t outleft,
                        int flags);
typedef int (*mbencodeinit_func)(MultibyteCodec_State *state,
                                 const struct _multibyte_codec *codec);
typedef pypymbc_ssize_t (*mbencodereset_func)(MultibyteCodec_State *state,
                        const struct _multibyte_codec *codec,
                        unsigned char **outbuf, pypymbc_ssize_t outleft);
typedef pypymbc_ssize_t (*mbdecode_func)(MultibyteCodec_State *state,
                        const struct _multibyte_codec *codec,
                        const unsigned char **inbuf, pypymbc_ssize_t inleft,
                        struct pypy_cjk_dec_s *writer);
typedef int (*mbdecodeinit_func)(MultibyteCodec_State *state,
                                 const struct _multibyte_codec *codec);
typedef pypymbc_ssize_t (*mbdecodereset_func)(MultibyteCodec_State *state,
                                         const struct _multibyte_codec *codec);

typedef struct _multibyte_codec {
    const char *encoding;
    const void *config;
    mbcodec_init codecinit;
    mbencode_func encode;
    mbencodeinit_func encinit;
    mbencodereset_func encreset;
    mbdecode_func decode;
    mbdecodeinit_func decinit;
    mbdecodereset_func decreset;
    struct _cjk_mod_state *modstate;
} MultibyteCodec;


/* positive values for illegal sequences */
#define MBERR_TOOSMALL          (-1) /* insufficient output buffer space */
#define MBERR_TOOFEW            (-2) /* incomplete input buffer */
#define MBERR_INTERNAL          (-3) /* internal runtime error */
#define MBERR_NOMEMORY          (-4) /* out of memory */

#define MBENC_FLUSH             0x0001 /* encode all characters encodable */
#define MBENC_RESET             0x0002 /* reset after an encoding session */
#define MBENC_MAX               MBENC_FLUSH


/* Each _codecs_*.c file registers itself with one of these; see
   I_AM_A_MODULE_FOR() in cjkcodecs.h.  In CPython the mapping tables are
   exported between the modules as capsules; here they are looked up by
   name in the registry. */

struct dbcs_map {
    const char *charset;
    const void *encmap;
    const void *decmap;
};

struct pypy_cjk_module_s {
    const char *name;
    void (*add_mappings)(void);
    void (*add_codecs)(void);
    struct dbcs_map *mapping_list;
    int num_mappings;
    MultibyteCodec *codec_list;
    int num_codecs;
    struct _cjk_mod_state *modstate;
    int initialized;
};

RPY_EXTERN
const MultibyteCodec *pypy_cjk_getcodec(const char *name);
RPY_EXTERN
int pypy_cjk_importmap(const char *locale, const char *charset,
                       const void **encmap, const void **decmap);


struct pypy_cjk_dec_s {
  const MultibyteCodec *codec;
  MultibyteCodec_State state;
  const unsigned char *inbuf_start, *inbuf, *inbuf_end;
  pypymbc_ucs4_t *outbuf_start, *outbuf, *outbuf_end;
};

RPY_EXTERN
struct pypy_cjk_dec_s *pypy_cjk_dec_new(const MultibyteCodec *codec);
RPY_EXTERN
pypymbc_ssize_t pypy_cjk_dec_init(struct pypy_cjk_dec_s *d,
                             char *inbuf, pypymbc_ssize_t inlen);
RPY_EXTERN
void pypy_cjk_dec_free(struct pypy_cjk_dec_s *);
RPY_EXTERN
int pypy_cjk_dec_expand(struct pypy_cjk_dec_s *, pypymbc_ssize_t esize);
RPY_EXTERN
pypymbc_ssize_t pypy_cjk_dec_chunk(struct pypy_cjk_dec_s *);
RPY_EXTERN
pypymbc_ucs4_t *pypy_cjk_dec_outbuf(struct pypy_cjk_dec_s *);
RPY_EXTERN
pypymbc_ssize_t pypy_cjk_dec_outlen(struct pypy_cjk_dec_s *);
RPY_EXTERN
pypymbc_ssize_t pypy_cjk_dec_inbuf_remaining(struct pypy_cjk_dec_s *d);
RPY_EXTERN
pypymbc_ssize_t pypy_cjk_dec_inbuf_consumed(struct pypy_cjk_dec_s* d);
RPY_EXTERN
pypymbc_ssize_t pypy_cjk_dec_replace_on_error(struct pypy_cjk_dec_s* d,
                            pypymbc_ucs4_t *, pypymbc_ssize_t, pypymbc_ssize_t);

struct pypy_cjk_enc_s {
  const MultibyteCodec *codec;
  MultibyteCodec_State state;
  const pypymbc_ucs4_t *inbuf_start;
  pypymbc_ssize_t inpos, inlen;
  unsigned char *outbuf_start, *outbuf, *outbuf_end;
};

RPY_EXTERN
struct pypy_cjk_enc_s *pypy_cjk_enc_new(const MultibyteCodec *codec);
RPY_EXTERN
pypymbc_ssize_t pypy_cjk_enc_init(struct pypy_cjk_enc_s *d,
                             pypymbc_ucs4_t *inbuf, pypymbc_ssize_t inlen);
RPY_EXTERN
void pypy_cjk_enc_free(struct pypy_cjk_enc_s *);
RPY_EXTERN
pypymbc_ssize_t pypy_cjk_enc_chunk(struct pypy_cjk_enc_s *, pypymbc_ssize_t);
RPY_EXTERN
pypymbc_ssize_t pypy_cjk_enc_reset(struct pypy_cjk_enc_s *);
RPY_EXTERN
char *pypy_cjk_enc_outbuf(struct pypy_cjk_enc_s *);
RPY_EXTERN
pypymbc_ssize_t pypy_cjk_enc_outlen(struct pypy_cjk_enc_s *);
RPY_EXTERN
pypymbc_ssize_t pypy_cjk_enc_inbuf_remaining(struct pypy_cjk_enc_s *d);
RPY_EXTERN
pypymbc_ssize_t pypy_cjk_enc_inbuf_consumed(struct pypy_cjk_enc_s* d);
RPY_EXTERN
pypymbc_ssize_t pypy_cjk_enc_replace_on_error(struct pypy_cjk_enc_s* d,
                                      char *, pypymbc_ssize_t, pypymbc_ssize_t);
RPY_EXTERN
const MultibyteCodec *pypy_cjk_enc_getcodec(struct pypy_cjk_enc_s *);
RPY_EXTERN
void pypy_cjk_enc_copystate(struct pypy_cjk_enc_s *dst, struct pypy_cjk_enc_s *src);
RPY_EXTERN
void pypy_cjk_enc_getstate(struct pypy_cjk_enc_s *d, unsigned char *buf);
RPY_EXTERN
void pypy_cjk_enc_setstate(struct pypy_cjk_enc_s *d, const unsigned char *buf);


#endif
