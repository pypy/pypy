
#ifndef _PYPY_MULTIBYTECODEC_H_
#define _PYPY_MULTIBYTECODEC_H_


#include <stddef.h>
#include <stdint.h>
#include <unistd.h>
#include <assert.h>

#define Py_UNICODE_SIZE  4
typedef uint32_t ucs4_t, Py_UNICODE;
typedef uint16_t ucs2_t, DBCHAR;
typedef ssize_t Py_ssize_t;


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

#endif
