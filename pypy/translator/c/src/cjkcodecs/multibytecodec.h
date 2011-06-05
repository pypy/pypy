
#ifndef _PYPY_MULTIBYTECODEC_H_
#define _PYPY_MULTIBYTECODEC_H_


#include <stddef.h>
#include <assert.h>

#ifdef _WIN64
typedef __int64 ssize_t
#elif defined(_WIN32)
typedef int ssize_t;
#else
#include <unistd.h>
#endif

#ifndef Py_UNICODE_SIZE
#ifdef _WIN32
#define Py_UNICODE_SIZE 2
#else
#define Py_UNICODE_SIZE 4
#endif
typedef wchar_t Py_UNICODE;
typedef ssize_t Py_ssize_t;
#define PY_SSIZE_T_MAX   ((Py_ssize_t)(((size_t) -1) >> 1))
#endif

#ifdef _WIN32
typedef unsigned int ucs4_t;
typedef unsigned short ucs2_t, DBCHAR;
#else
#include <stdint.h>
typedef uint32_t ucs4_t;
typedef uint16_t ucs2_t, DBCHAR;
#endif



typedef union {
    void *p;
    int i;
    unsigned char c[8];
    ucs2_t u2[4];
    ucs4_t u4[2];
} MultibyteCodec_State;

typedef int (*mbcodec_init)(const void *config);
typedef Py_ssize_t (*mbencode_func)(MultibyteCodec_State *state,
                        const void *config,
                        const Py_UNICODE **inbuf, Py_ssize_t inleft,
                        unsigned char **outbuf, Py_ssize_t outleft,
                        int flags);
typedef int (*mbencodeinit_func)(MultibyteCodec_State *state,
                                 const void *config);
typedef Py_ssize_t (*mbencodereset_func)(MultibyteCodec_State *state,
                        const void *config,
                        unsigned char **outbuf, Py_ssize_t outleft);
typedef Py_ssize_t (*mbdecode_func)(MultibyteCodec_State *state,
                        const void *config,
                        const unsigned char **inbuf, Py_ssize_t inleft,
                        Py_UNICODE **outbuf, Py_ssize_t outleft);
typedef int (*mbdecodeinit_func)(MultibyteCodec_State *state,
                                 const void *config);
typedef Py_ssize_t (*mbdecodereset_func)(MultibyteCodec_State *state,
                                         const void *config);

typedef struct MultibyteCodec_s {
    const char *encoding;
    const void *config;
    mbcodec_init codecinit;
    mbencode_func encode;
    mbencodeinit_func encinit;
    mbencodereset_func encreset;
    mbdecode_func decode;
    mbdecodeinit_func decinit;
    mbdecodereset_func decreset;
} MultibyteCodec;


/* positive values for illegal sequences */
#define MBERR_TOOSMALL          (-1) /* insufficient output buffer space */
#define MBERR_TOOFEW            (-2) /* incomplete input buffer */
#define MBERR_INTERNAL          (-3) /* internal runtime error */
#define MBERR_NOMEMORY          (-4) /* out of memory */

#define MBENC_FLUSH             0x0001 /* encode all characters encodable */
#define MBENC_MAX               MBENC_FLUSH


struct pypy_cjk_dec_s {
  const MultibyteCodec *codec;
  MultibyteCodec_State state;
  const unsigned char *inbuf_start, *inbuf, *inbuf_end;
  Py_UNICODE *outbuf_start, *outbuf, *outbuf_end;
};

struct pypy_cjk_dec_s *pypy_cjk_dec_init(const MultibyteCodec *codec,
                                         char *inbuf, Py_ssize_t inlen);
void pypy_cjk_dec_free(struct pypy_cjk_dec_s *);
Py_ssize_t pypy_cjk_dec_chunk(struct pypy_cjk_dec_s *);
Py_UNICODE *pypy_cjk_dec_outbuf(struct pypy_cjk_dec_s *);
Py_ssize_t pypy_cjk_dec_outlen(struct pypy_cjk_dec_s *);
Py_ssize_t pypy_cjk_dec_inbuf_remaining(struct pypy_cjk_dec_s *d);
Py_ssize_t pypy_cjk_dec_inbuf_consumed(struct pypy_cjk_dec_s* d);
void pypy_cjk_dec_inbuf_add(struct pypy_cjk_dec_s*, Py_ssize_t);

struct pypy_cjk_enc_s {
  const MultibyteCodec *codec;
  MultibyteCodec_State state;
  const Py_UNICODE *inbuf_start, *inbuf, *inbuf_end;
  unsigned char *outbuf_start, *outbuf, *outbuf_end;
};

struct pypy_cjk_enc_s *pypy_cjk_enc_init(const MultibyteCodec *codec,
                                         Py_UNICODE *inbuf, Py_ssize_t inlen);
void pypy_cjk_enc_free(struct pypy_cjk_enc_s *);
Py_ssize_t pypy_cjk_enc_chunk(struct pypy_cjk_enc_s *);
Py_ssize_t pypy_cjk_enc_reset(struct pypy_cjk_enc_s *);
char *pypy_cjk_enc_outbuf(struct pypy_cjk_enc_s *);
Py_ssize_t pypy_cjk_enc_outlen(struct pypy_cjk_enc_s *);
Py_ssize_t pypy_cjk_enc_inbuf_remaining(struct pypy_cjk_enc_s *d);
Py_ssize_t pypy_cjk_enc_inbuf_consumed(struct pypy_cjk_enc_s* d);

/* list of codecs defined in the .c files */

#define DEFINE_CODEC(name)                              \
    const MultibyteCodec *pypy_cjkcodec_##name(void);

// _codecs_cn
DEFINE_CODEC(gb2312)
DEFINE_CODEC(gbk)
DEFINE_CODEC(gb18030)
DEFINE_CODEC(hz)

//_codecs_hk
DEFINE_CODEC(big5hkscs)

//_codecs_iso2022
DEFINE_CODEC(iso2022_kr)
DEFINE_CODEC(iso2022_jp)
DEFINE_CODEC(iso2022_jp_1)
DEFINE_CODEC(iso2022_jp_2)
DEFINE_CODEC(iso2022_jp_2004)
DEFINE_CODEC(iso2022_jp_3)
DEFINE_CODEC(iso2022_jp_ext)

//_codecs_jp
DEFINE_CODEC(shift_jis)
DEFINE_CODEC(cp932)
DEFINE_CODEC(euc_jp)
DEFINE_CODEC(shift_jis_2004)
DEFINE_CODEC(euc_jis_2004)
DEFINE_CODEC(euc_jisx0213)
DEFINE_CODEC(shift_jisx0213)

//_codecs_kr
DEFINE_CODEC(euc_kr)
DEFINE_CODEC(cp949)
DEFINE_CODEC(johab)

//_codecs_tw
DEFINE_CODEC(big5)
DEFINE_CODEC(cp950)


#endif
