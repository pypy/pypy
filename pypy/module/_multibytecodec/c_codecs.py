import py, sys
from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rpython.lltypesystem.rstr import UNICODE
from pypy.rpython.annlowlevel import hlunicode
from pypy.rlib.objectmodel import keepalive_until_here
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


srcdir = py.path.local(pypydir).join('module', '_multibytecodec', 'cjkcodecs')

eci = ExternalCompilationInfo(
    separate_module_files = [
        srcdir.join('_codecs_cn.c'),
        srcdir.join('_codecs_hk.c'),
        srcdir.join('_codecs_iso2022.c'),
        srcdir.join('_codecs_jp.c'),
        srcdir.join('_codecs_kr.c'),
        srcdir.join('_codecs_tw.c'),
        srcdir.join('multibytecodec.c'),
    ],
)

MBERR_TOOSMALL = -1  # insufficient output buffer space
MBERR_TOOFEW   = -2  # incomplete input buffer
MBERR_INTERNAL = -3  # internal runtime error
MBERR_NOMEMORY = -4  # out of memory

MULTIBYTECODEC_P = rffi.COpaquePtr('struct MultibyteCodec_s',
                                   compilation_info=eci)

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

def decode(codec, stringdata):
    inleft = len(stringdata)
    if inleft > sys.maxint // 4:
        raise MemoryError
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
                multibytecodec_decerror(decodebuf, r)
            src = pypy_cjk_dec_outbuf(decodebuf)
            length = pypy_cjk_dec_outlen(decodebuf)
            return unicode_from_raw(src, length)
        #
        finally:
            pypy_cjk_dec_free(decodebuf)
    #
    finally:
        rffi.free_nonmovingbuffer(stringdata, inbuf)

def multibytecodec_decerror(decodebuf, e):
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
    # if errors == ERROR_REPLACE:...
    # if errors == ERROR_IGNORE or errors == ERROR_REPLACE:...
    start = pypy_cjk_dec_inbuf_consumed(decodebuf)
    end = start + esize
    if 1:  # errors == ERROR_STRICT:
        raise EncodeDecodeError(start, end, reason)

# ____________________________________________________________

def unicode_from_raw(src, length):
    result = lltype.malloc(UNICODE, length)
    try:
        uni_chars_offset = (rffi.offsetof(UNICODE, 'chars') + \
                            rffi.itemoffsetof(UNICODE.chars, 0))
        dest = rffi.cast_ptr_to_adr(result) + uni_chars_offset
        src = rffi.cast_ptr_to_adr(src) + rffi.itemoffsetof(rffi.CWCHARP.TO)
        rffi.raw_memcopy(src, dest,
                         llmemory.sizeof(lltype.UniChar) * length)
        return hlunicode(result)
    finally:
        keepalive_until_here(result)
