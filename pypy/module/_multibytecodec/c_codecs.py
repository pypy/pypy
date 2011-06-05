import py, sys
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.tool.autopath import pypydir


class EncodeDecodeError(Exception):
    def __init__(self, start, end, reason):
        self.start = start
        self.end = end
        self.reason = reason
    def __repr__(self):
        return 'EncodeDecodeError(%r, %r, %r)' % (self.start, self.end,
                                                  self.reason)

srcdir = py.path.local(pypydir).join('translator', 'c')

codecs = [
    # _codecs_cn
    'gb2312', 'gbk', 'gb18030', 'hz',

    # _codecs_hk
    'big5hkscs',

    # _codecs_iso2022
    'iso2022_kr', 'iso2022_jp', 'iso2022_jp_1', 'iso2022_jp_2',
    'iso2022_jp_2004', 'iso2022_jp_3', 'iso2022_jp_ext',

    # _codecs_jp
    'shift_jis', 'cp932', 'euc_jp', 'shift_jis_2004',
    'euc_jis_2004', 'euc_jisx0213', 'shift_jisx0213',

    # _codecs_kr
    'euc_kr', 'cp949', 'johab',

    # _codecs_tw
    'big5', 'cp950',
]

eci = ExternalCompilationInfo(
    separate_module_files = [
        srcdir.join('src', 'cjkcodecs', '_codecs_cn.c'),
        srcdir.join('src', 'cjkcodecs', '_codecs_hk.c'),
        srcdir.join('src', 'cjkcodecs', '_codecs_iso2022.c'),
        srcdir.join('src', 'cjkcodecs', '_codecs_jp.c'),
        srcdir.join('src', 'cjkcodecs', '_codecs_kr.c'),
        srcdir.join('src', 'cjkcodecs', '_codecs_tw.c'),
        srcdir.join('src', 'cjkcodecs', 'multibytecodec.c'),
    ],
    includes = ['src/cjkcodecs/multibytecodec.h'],
    include_dirs = [str(srcdir)],
    export_symbols = [
        "pypy_cjk_dec_init", "pypy_cjk_dec_free", "pypy_cjk_dec_chunk",
        "pypy_cjk_dec_outbuf", "pypy_cjk_dec_outlen",
        "pypy_cjk_dec_inbuf_remaining", "pypy_cjk_dec_inbuf_consumed",

        "pypy_cjk_enc_init", "pypy_cjk_enc_free", "pypy_cjk_enc_chunk",
        "pypy_cjk_enc_reset", "pypy_cjk_enc_outbuf", "pypy_cjk_enc_outlen",
        "pypy_cjk_enc_inbuf_remaining", "pypy_cjk_enc_inbuf_consumed",
    ] + ["pypy_cjkcodec_%s" % codec for codec in codecs],
)

MBERR_TOOSMALL = -1  # insufficient output buffer space
MBERR_TOOFEW   = -2  # incomplete input buffer
MBERR_INTERNAL = -3  # internal runtime error
MBERR_NOMEMORY = -4  # out of memory

MULTIBYTECODEC_P = rffi.COpaquePtr('struct MultibyteCodec_s',
                                   compilation_info=eci)

def llexternal(*args, **kwds):
    kwds.setdefault('compilation_info', eci)
    kwds.setdefault('sandboxsafe', True)
    kwds.setdefault('_nowrapper', True)
    return rffi.llexternal(*args, **kwds)

def getter_for(name):
    return llexternal('pypy_cjkcodec_%s' % name, [], MULTIBYTECODEC_P)

_codecs_getters = dict([(name, getter_for(name)) for name in codecs])
assert len(_codecs_getters) == len(codecs)

def getcodec(name):
    getter = _codecs_getters[name]
    return getter()

# ____________________________________________________________
# Decoding

DECODEBUF_P = rffi.COpaquePtr('struct pypy_cjk_dec_s', compilation_info=eci)
pypy_cjk_dec_init = llexternal('pypy_cjk_dec_init',
                               [MULTIBYTECODEC_P, rffi.CCHARP, rffi.SSIZE_T],
                               DECODEBUF_P)
pypy_cjk_dec_free = llexternal('pypy_cjk_dec_free', [DECODEBUF_P],
                               lltype.Void)
pypy_cjk_dec_chunk = llexternal('pypy_cjk_dec_chunk', [DECODEBUF_P],
                                rffi.SSIZE_T)
pypy_cjk_dec_outbuf = llexternal('pypy_cjk_dec_outbuf', [DECODEBUF_P],
                                 rffi.CWCHARP)
pypy_cjk_dec_outlen = llexternal('pypy_cjk_dec_outlen', [DECODEBUF_P],
                                 rffi.SSIZE_T)
pypy_cjk_dec_inbuf_remaining = llexternal('pypy_cjk_dec_inbuf_remaining',
                                          [DECODEBUF_P], rffi.SSIZE_T)
pypy_cjk_dec_inbuf_consumed = llexternal('pypy_cjk_dec_inbuf_consumed',
                                         [DECODEBUF_P], rffi.SSIZE_T)
pypy_cjk_dec_inbuf_add = llexternal('pypy_cjk_dec_inbuf_add',
                                    [DECODEBUF_P, rffi.SSIZE_T, rffi.INT],
                                    rffi.INT)

def decode(codec, stringdata, errors="strict"):
    inleft = len(stringdata)
    inbuf = rffi.get_nonmovingbuffer(stringdata)
    try:
        decodebuf = pypy_cjk_dec_init(codec, inbuf, inleft)
        if not decodebuf:
            raise MemoryError
        try:
            while True:
                r = pypy_cjk_dec_chunk(decodebuf)
                if r == 0:
                    break
                multibytecodec_decerror(decodebuf, r, errors)
            src = pypy_cjk_dec_outbuf(decodebuf)
            length = pypy_cjk_dec_outlen(decodebuf)
            return rffi.wcharpsize2unicode(src, length)
        #
        finally:
            pypy_cjk_dec_free(decodebuf)
    #
    finally:
        rffi.free_nonmovingbuffer(stringdata, inbuf)

def multibytecodec_decerror(decodebuf, e, errors):
    if e > 0:
        reason = "illegal multibyte sequence"
        esize = e
    elif e == MBERR_TOOFEW:
        reason = "incomplete multibyte sequence"
        esize = pypy_cjk_dec_inbuf_remaining(decodebuf)
    elif e == MBERR_NOMEMORY:
        raise MemoryError
    else:
        raise RuntimeError
    #
    if errors == "ignore":
        pypy_cjk_dec_inbuf_add(decodebuf, esize, 0)
        return     # continue decoding
    if errors == "replace":
        e = pypy_cjk_dec_inbuf_add(decodebuf, esize, 1)
        if e == MBERR_NOMEMORY:
            raise MemoryError
        return     # continue decoding
    start = pypy_cjk_dec_inbuf_consumed(decodebuf)
    end = start + esize
    if errors != "strict":
        reason = "not implemented: custom error handlers"   # XXX implement me
    raise EncodeDecodeError(start, end, reason)

# ____________________________________________________________
# Encoding
ENCODEBUF_P = rffi.COpaquePtr('struct pypy_cjk_enc_s', compilation_info=eci)
pypy_cjk_enc_init = llexternal('pypy_cjk_enc_init',
                               [MULTIBYTECODEC_P, rffi.CWCHARP, rffi.SSIZE_T],
                               ENCODEBUF_P)
pypy_cjk_enc_free = llexternal('pypy_cjk_enc_free', [ENCODEBUF_P],
                               lltype.Void)
pypy_cjk_enc_chunk = llexternal('pypy_cjk_enc_chunk', [ENCODEBUF_P],
                                rffi.SSIZE_T)
pypy_cjk_enc_reset = llexternal('pypy_cjk_enc_reset', [ENCODEBUF_P],
                                rffi.SSIZE_T)
pypy_cjk_enc_outbuf = llexternal('pypy_cjk_enc_outbuf', [ENCODEBUF_P],
                                 rffi.CCHARP)
pypy_cjk_enc_outlen = llexternal('pypy_cjk_enc_outlen', [ENCODEBUF_P],
                                 rffi.SSIZE_T)
pypy_cjk_enc_inbuf_remaining = llexternal('pypy_cjk_enc_inbuf_remaining',
                                          [ENCODEBUF_P], rffi.SSIZE_T)
pypy_cjk_enc_inbuf_consumed = llexternal('pypy_cjk_enc_inbuf_consumed',
                                         [ENCODEBUF_P], rffi.SSIZE_T)

def encode(codec, unicodedata):
    inleft = len(unicodedata)
    inbuf = rffi.get_nonmoving_unicodebuffer(unicodedata)
    try:
        encodebuf = pypy_cjk_enc_init(codec, inbuf, inleft)
        if not encodebuf:
            raise MemoryError
        try:
            r = pypy_cjk_enc_chunk(encodebuf)
            if r != 0:
                multibytecodec_encerror(encodebuf, r)
                assert False
            r = pypy_cjk_enc_reset(encodebuf)
            if r != 0:
                multibytecodec_encerror(encodebuf, r)
                assert False
            src = pypy_cjk_enc_outbuf(encodebuf)
            length = pypy_cjk_enc_outlen(encodebuf)
            return rffi.charpsize2str(src, length)
        #
        finally:
            pypy_cjk_enc_free(encodebuf)
    #
    finally:
        rffi.free_nonmoving_unicodebuffer(unicodedata, inbuf)

def multibytecodec_encerror(encodebuf, e):
    if e > 0:
        reason = "illegal multibyte sequence"
        esize = e
    elif e == MBERR_TOOFEW:
        reason = "incomplete multibyte sequence"
        esize = pypy_cjk_enc_inbuf_remaining(encodebuf)
    elif e == MBERR_NOMEMORY:
        raise MemoryError
    else:
        raise RuntimeError
    #
    # if errors == ERROR_REPLACE:...
    # if errors == ERROR_IGNORE or errors == ERROR_REPLACE:...
    start = pypy_cjk_enc_inbuf_consumed(encodebuf)
    end = start + esize
    if 1:  # errors == ERROR_STRICT:
        raise EncodeDecodeError(start, end, reason)
