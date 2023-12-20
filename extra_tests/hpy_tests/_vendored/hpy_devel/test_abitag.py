from hpy.devel.abitag import parse_ext_suffix, get_hpy_ext_suffix, HPY_ABI_TAG

def test_parse_ext_suffix_ext():
    _, ext = parse_ext_suffix('.cpython-310-x86_64-linux-gnu.so')
    assert ext == 'so'

def test_parse_ext_suffix_abi_tag():
    def abi_tag(suffix):
        tag, ext = parse_ext_suffix(suffix)
        return tag

    assert abi_tag('.cpython-38-x86_64-linux-gnu.so') == 'cp38'
    assert abi_tag('.cpython-38d-x86_64-linux-gnu.so') == 'cp38d'
    assert abi_tag('.cpython-310-x86_64-linux-gnu.so') == 'cp310'
    assert abi_tag('.cpython-310d-x86_64-linux-gnu.so') == 'cp310d'
    assert abi_tag('.cpython-310-darwin.so') == 'cp310'
    assert abi_tag('.cp310-win_amd64.pyd') == 'cp310'
    assert abi_tag('.pypy38-pp73-x86_64-linux-gnu.so') == 'pypy38-pp73'
    assert abi_tag('.graalpy-38-native-x86_64-darwin.dylib') == 'graalpy-38-native'

def test_get_hpy_ext_suffix():
    get = get_hpy_ext_suffix
    hpy0 = HPY_ABI_TAG
    assert get('universal', '.cpython-38-x86_64-linux-gnu.so') == f'.{hpy0}.so'
    assert get('hybrid', '.cpython-38-x86_64-linux-gnu.so') == f'.{hpy0}-cp38.so'
