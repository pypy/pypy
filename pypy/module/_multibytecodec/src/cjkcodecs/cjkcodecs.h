/*
 * cjkcodecs.h: common header for cjkcodecs
 *
 * Written by Hye-Shik Chang <perky@FreeBSD.org>
 *
 * PyPy version: this follows CPython's Modules/cjkcodecs/cjkcodecs.h
 * (3.12) with the Python C API replaced by the glue in multibytecodec.c,
 * so that the _codecs_*.c files can be verbatim copies of CPython's.
 */

#ifndef _CJKCODECS_H_
#define _CJKCODECS_H_

#include "src/cjkcodecs/multibytecodec.h"
#include "src/cjkcodecs/fixnames.h"


/* a unicode "undefined" code point */
#define UNIINV  0xFFFE

/* internal-use DBCS code points which aren't used by any charsets */
#define NOCHAR  0xFFFF
#define MULTIC  0xFFFE
#define DBCINV  0xFFFD

/* shorter macros to save source size of mapping tables */
#define U UNIINV
#define N NOCHAR
#define M MULTIC
#define D DBCINV

struct dbcs_index {
    const ucs2_t *map;
    unsigned char bottom, top;
};
typedef struct dbcs_index decode_map;

struct widedbcs_index {
    const Py_UCS4 *map;
    unsigned char bottom, top;
};
typedef struct widedbcs_index widedecode_map;

struct unim_index {
    const DBCHAR *map;
    unsigned char bottom, top;
};
typedef struct unim_index encode_map;

struct unim_index_bytebased {
    const unsigned char *map;
    unsigned char bottom, top;
};

struct pair_encodemap {
    Py_UCS4 uniseq;
    DBCHAR code;
};

#ifndef CJK_MOD_SPECIFIC_STATE
#define CJK_MOD_SPECIFIC_STATE
#endif

typedef struct _cjk_mod_state {
    int num_mappings;
    int num_codecs;
    struct dbcs_map *mapping_list;
    MultibyteCodec *codec_list;

    CJK_MOD_SPECIFIC_STATE
} cjkcodecs_module_state;

#define CODEC_INIT(encoding)                                            \
    static int encoding##_codec_init(const MultibyteCodec *codec)

#define ENCODER_INIT(encoding)                                          \
    static int encoding##_encode_init(                                  \
        MultibyteCodec_State *state, const MultibyteCodec *codec)
#define ENCODER(encoding)                                               \
    static Py_ssize_t encoding##_encode(                                \
        MultibyteCodec_State *state, const MultibyteCodec *codec,       \
        int kind, const void *data,                                     \
        Py_ssize_t *inpos, Py_ssize_t inlen,                            \
        unsigned char **outbuf, Py_ssize_t outleft, int flags)
#define ENCODER_RESET(encoding)                                         \
    static Py_ssize_t encoding##_encode_reset(                          \
        MultibyteCodec_State *state, const MultibyteCodec *codec,       \
        unsigned char **outbuf, Py_ssize_t outleft)

#define DECODER_INIT(encoding)                                          \
    static int encoding##_decode_init(                                  \
        MultibyteCodec_State *state, const MultibyteCodec *codec)
#define DECODER(encoding)                                               \
    static Py_ssize_t encoding##_decode(                                \
        MultibyteCodec_State *state, const MultibyteCodec *codec,       \
        const unsigned char **inbuf, Py_ssize_t inleft,                 \
        _PyUnicodeWriter *writer)
#define DECODER_RESET(encoding)                                         \
    static Py_ssize_t encoding##_decode_reset(                          \
        MultibyteCodec_State *state, const MultibyteCodec *codec)

#define NEXT_IN(i)                              \
    do {                                        \
        (*inbuf) += (i);                        \
        (inleft) -= (i);                        \
    } while (0)
#define NEXT_INCHAR(i)                          \
    do {                                        \
        (*inpos) += (i);                        \
    } while (0)
#define NEXT_OUT(o)                             \
    do {                                        \
        (*outbuf) += (o);                       \
        (outleft) -= (o);                       \
    } while (0)
#define NEXT(i, o)                              \
    do {                                        \
        NEXT_INCHAR(i);                         \
        NEXT_OUT(o);                            \
    } while (0)

#define REQUIRE_INBUF(n)                        \
    do {                                        \
        if (inleft < (n))                       \
            return MBERR_TOOFEW;                \
    } while (0)

#define REQUIRE_OUTBUF(n)                       \
    do {                                        \
        if (outleft < (n))                      \
            return MBERR_TOOSMALL;              \
    } while (0)

#define INBYTE1 ((*inbuf)[0])
#define INBYTE2 ((*inbuf)[1])
#define INBYTE3 ((*inbuf)[2])
#define INBYTE4 ((*inbuf)[3])

/* the RPython side always passes the input as an array of Py_UCS4 */
#define PyUnicode_READ(kind, data, index) (((const Py_UCS4 *)(data))[index])

#define INCHAR1 (PyUnicode_READ(kind, data, *inpos))
#define INCHAR2 (PyUnicode_READ(kind, data, *inpos + 1))

#define OUTCHAR(c)                                                         \
    do {                                                                   \
        if (writer->outbuf >= writer->outbuf_end &&                        \
            pypy_cjk_dec_expand(writer, 1) < 0)                            \
            return MBERR_NOMEMORY;                                         \
        *writer->outbuf++ = (Py_UCS4)(c);                                  \
    } while (0)

#define OUTCHAR2(c1, c2)                                                   \
    do {                                                                   \
        if (writer->outbuf + 2 > writer->outbuf_end &&                     \
            pypy_cjk_dec_expand(writer, 2) < 0)                            \
            return MBERR_NOMEMORY;                                         \
        writer->outbuf[0] = (Py_UCS4)(c1);                                 \
        writer->outbuf[1] = (Py_UCS4)(c2);                                 \
        writer->outbuf += 2;                                               \
    } while (0)

#define OUTBYTEI(c, i)                     \
    do {                                   \
        assert((unsigned char)(c) == (c)); \
        ((*outbuf)[i]) = (c);              \
    } while (0)

#define OUTBYTE1(c) OUTBYTEI(c, 0)
#define OUTBYTE2(c) OUTBYTEI(c, 1)
#define OUTBYTE3(c) OUTBYTEI(c, 2)
#define OUTBYTE4(c) OUTBYTEI(c, 3)

#define WRITEBYTE1(c1)              \
    do {                            \
        REQUIRE_OUTBUF(1);          \
        OUTBYTE1(c1);               \
    } while (0)
#define WRITEBYTE2(c1, c2)          \
    do {                            \
        REQUIRE_OUTBUF(2);          \
        OUTBYTE1(c1);               \
        OUTBYTE2(c2);               \
    } while (0)
#define WRITEBYTE3(c1, c2, c3)      \
    do {                            \
        REQUIRE_OUTBUF(3);          \
        OUTBYTE1(c1);               \
        OUTBYTE2(c2);               \
        OUTBYTE3(c3);               \
    } while (0)
#define WRITEBYTE4(c1, c2, c3, c4)  \
    do {                            \
        REQUIRE_OUTBUF(4);          \
        OUTBYTE1(c1);               \
        OUTBYTE2(c2);               \
        OUTBYTE3(c3);               \
        OUTBYTE4(c4);               \
    } while (0)

#define _TRYMAP_ENC(m, assi, val)                               \
    ((m)->map != NULL && (val) >= (m)->bottom &&                \
        (val)<= (m)->top && ((assi) = (m)->map[(val) -          \
        (m)->bottom]) != NOCHAR)
#define TRYMAP_ENC(charset, assi, uni)                     \
    _TRYMAP_ENC(&charset##_encmap[(uni) >> 8], assi, (uni) & 0xff)
#define TRYMAP_ENC_ST(charset, assi, uni) \
    _TRYMAP_ENC(&(codec->modstate->charset##_encmap)[(uni) >> 8], \
                assi, (uni) & 0xff)

#define _TRYMAP_DEC(m, assi, val)                             \
    ((m)->map != NULL &&                                        \
     (val) >= (m)->bottom &&                                    \
     (val)<= (m)->top &&                                        \
     ((assi) = (m)->map[(val) - (m)->bottom]) != UNIINV)
#define TRYMAP_DEC(charset, assi, c1, c2)                     \
    _TRYMAP_DEC(&charset##_decmap[c1], assi, c2)
#define TRYMAP_DEC_ST(charset, assi, c1, c2) \
    _TRYMAP_DEC(&(codec->modstate->charset##_decmap)[c1], assi, c2)

/* The lists of mappings and codecs are filled in at first use by
   multibytecodec.c, see pypy_cjk_getcodec(). */

#define BEGIN_MAPPINGS_LIST(NUM)                                    \
enum { _pypy_num_mappings = (NUM) };                                \
static struct dbcs_map _pypy_mapping_list[(NUM) + 1];               \
static void                                                         \
add_mappings(void)                                                  \
{                                                                   \
    int idx = 0;                                                    \
    (void)idx;

#define MAPPING_ENCONLY(enc) \
    _pypy_mapping_list[idx++] = (struct dbcs_map){#enc, (void*)enc##_encmap, NULL};
#define MAPPING_DECONLY(enc) \
    _pypy_mapping_list[idx++] = (struct dbcs_map){#enc, NULL, (void*)enc##_decmap};
#define MAPPING_ENCDEC(enc) \
    _pypy_mapping_list[idx++] = (struct dbcs_map){#enc, (void*)enc##_encmap, (void*)enc##_decmap};

#define END_MAPPINGS_LIST               \
    assert(_pypy_num_mappings == idx);  \
}

#define BEGIN_CODECS_LIST(NUM)                                  \
enum { _pypy_num_codecs = (NUM) };                              \
static MultibyteCodec _pypy_codec_list[(NUM) + 1];              \
static void                                                     \
add_codecs(void)                                                \
{                                                               \
    int idx = 0;                                                \
    (void)idx;

#define _STATEFUL_METHODS(enc)          \
    enc##_encode,                       \
    enc##_encode_init,                  \
    enc##_encode_reset,                 \
    enc##_decode,                       \
    enc##_decode_init,                  \
    enc##_decode_reset,
#define _STATELESS_METHODS(enc)         \
    enc##_encode, NULL, NULL,           \
    enc##_decode, NULL, NULL,

#define NEXT_CODEC \
    _pypy_codec_list[idx++]

#define CODEC_STATEFUL(enc) \
    NEXT_CODEC = (MultibyteCodec){#enc, NULL, NULL, _STATEFUL_METHODS(enc)};
#define CODEC_STATELESS(enc) \
    NEXT_CODEC = (MultibyteCodec){#enc, NULL, NULL, _STATELESS_METHODS(enc)};
#define CODEC_STATELESS_WINIT(enc) \
    NEXT_CODEC = (MultibyteCodec){#enc, NULL, enc##_codec_init, _STATELESS_METHODS(enc)};

#define END_CODECS_LIST                         \
    assert(_pypy_num_codecs == idx);            \
}


#ifdef USING_BINARY_PAIR_SEARCH
static DBCHAR
find_pairencmap(ucs2_t body, ucs2_t modifier,
                const struct pair_encodemap *haystack, int haystacksize)
{
    int pos, min, max;
    Py_UCS4 value = body << 16 | modifier;

    min = 0;
    max = haystacksize;

    for (pos = haystacksize >> 1; min != max; pos = (min + max) >> 1) {
        if (value < haystack[pos].uniseq) {
            if (max != pos) {
                max = pos;
                continue;
            }
        }
        else if (value > haystack[pos].uniseq) {
            if (min != pos) {
                min = pos;
                continue;
            }
        }
        break;
    }

    if (value == haystack[pos].uniseq) {
        return haystack[pos].code;
    }
    return DBCINV;
}
#endif

#ifdef USING_IMPORTED_MAPS
#define IMPORT_MAP(locale, charset, encmap, decmap) \
    pypy_cjk_importmap(#locale, #charset, \
                       (const void**)encmap, (const void**)decmap)
#endif

#define I_AM_A_MODULE_FOR(loc)                                          \
    static cjkcodecs_module_state _pypy_modstate;                       \
    RPY_EXTERN struct pypy_cjk_module_s pypy_cjkmodule_##loc;           \
    struct pypy_cjk_module_s pypy_cjkmodule_##loc = {                   \
        #loc, add_mappings, add_codecs,                                 \
        _pypy_mapping_list, _pypy_num_mappings,                         \
        _pypy_codec_list, _pypy_num_codecs,                             \
        &_pypy_modstate, 0 };

#endif
