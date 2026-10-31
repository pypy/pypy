from email.parser import Parser

from pathlib import Path
from urllib.request import urlopen

import cffi
import pypy
import pytest

repo_root = Path(pypy.__file__).parent.parent
metadata = repo_root / 'lib_pypy' / 'cffi-2.1.0.dist-info' / 'METADATA'

def test_metadata():
    info = Parser().parsestr(metadata.read_text(encoding='utf-8'))
    assert info['version'] == cffi.__version__

@pytest.mark.skipif('sys.version_info[0] < 3', reason="upstream is python3-only")
def test_pycparser_version():
    url = 'https://raw.githubusercontent.com/eliben/pycparser/master/pycparser/__init__.py'
    source = urlopen(url).read().decode('utf8')
    dest = (Path(__file__).parent.parent.parent / 'lib_pypy' / 'cffi' /
            '_pycparser' / '__init__.py').read_text(encoding='utf-8')
    # if this fails, the vendored pycparser is not the latest version
    # lib_pypy/cffi/_pycparser/README
    assert source.strip() == dest.strip()
