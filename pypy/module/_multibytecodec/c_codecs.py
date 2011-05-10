import py
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.tool.autopath import pypydir


srcdir = py.path.local(pypydir).join('module', '_multibytecodec', 'cjkcodecs')

eci = ExternalCompilationInfo(
    separate_module_files = [
        srcdir.join('_codecs_cn.c'),
        srcdir.join('_codecs_hk.c'),
        srcdir.join('_codecs_iso2022.c'),
        srcdir.join('_codecs_jp.c'),
        srcdir.join('_codecs_kr.c'),
        srcdir.join('_codecs_tw.c'),
    ],
)


MULTIBYTECODEC_PTR = rffi.VOIDP

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

def getter_for(name):
    return rffi.llexternal('pypy_cjkcodec_%s' % name, [], MULTIBYTECODEC_PTR,
                           compilation_info=eci, sandboxsafe=True,
                           _nowrapper=True)

_codecs_getters = dict([(name, getter_for(name)) for name in codecs])

def getcodec(name):
    try:
        getter = _codecs_getters[name]
    except KeyError:
        return lltype.nullptr(MULTIBYTECODEC_PTR.TO)
    else:
        return getter()
