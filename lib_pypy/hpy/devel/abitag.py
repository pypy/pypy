import sys
from distutils import sysconfig

# NOTE: these must be kept on sync with the equivalent defines in hpy.h
HPY_ABI_VERSION = 0
HPY_ABI_VERSION_MINOR = 0
HPY_ABI_TAG = 'hpy%d' % HPY_ABI_VERSION

def parse_ext_suffix(ext_suffix=None):
    """
    Parse EXT_SUFFIX and return abi_tag, ext.

    - abi_tag is a string representing the CPython ABI tag: e.g. 'cp38', 'cp310d', etc.
    - ext is the filename extension, e.g 'so', 'pyd' or 'dylib'
    """
    if ext_suffix is None:
        ext_suffix = sysconfig.get_config_var('EXT_SUFFIX')

    # ext_suffix is something like this. We want to keep the parts which are
    # related to the ABI and remove the parts which are related to the
    # platform:
    #   - linux:   '.cpython-310-x86_64-linux-gnu.so'
    #   - mac:     '.cpython-310-darwin.so'
    #   - win:     '.cp310-win_amd64.pyd'
    #   - pypy:    '.pypy38-pp73-x86_64-linux-gnu.so'
    #   - graalpy: '.graalpy-38-native-x86_64-darwin.dylib'
    assert ext_suffix[0] == '.'
    _, soabi, ext = ext_suffix.split('.')

    # this is very ad-hoc but couldn't find a better way to do it
    parts = soabi.split('-')
    if parts[0].startswith('cpython'):      # cpython on linux, mac
        n = 2
    elif parts[0].startswith('cp'):         # cpython on windows
        n = 1
    elif parts[0].startswith('pypy'):       # pypy
        n = 2
    elif parts[0].startswith('graalpy'):    # graalpy
        n = 3
    else:                                   # none of the above, keep all parts
        n = len(parts)

    abi_tag = '-'.join(parts[:n])
    # on cpython linux/mac, abi is now cpython-310: shorten it ot cp310, like
    # on windows and on wheel tags
    abi_tag = abi_tag.replace('cpython-', 'cp')
    return abi_tag, ext


def get_hpy_ext_suffix(hpy_abi, ext_suffix=None):
    """
    Return the proper filename extension for the given hpy_abi.

    For example with CPython 3.10 on Linux, it will return:

      - universal ==> .hpy0.so
      - hybrid    ==> .hpy0-cp310.so
    """
    assert hpy_abi in ('cpython', 'universal', 'hybrid')
    cpy_abi_tag, ext = parse_ext_suffix(ext_suffix)
    if hpy_abi == 'cpython':
        return sysconfig.get_config_var('EXT_SUFFIX')
    elif hpy_abi == 'universal':
        return '.%s.%s' % (HPY_ABI_TAG, ext)
    else:
        return '.%s-%s.%s' % (HPY_ABI_TAG, cpy_abi_tag, ext)
