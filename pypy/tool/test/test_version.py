import os, sys
import py
from pypy.tool.version import get_repo_version_info, _get_hg_archive_version

def test_hg_archival_version(tmpdir):
    def version_for(name, **kw):
        path = tmpdir.join(name)
        path.write('\n'.join('%s: %s' % x for x in kw.items()))
        return _get_hg_archive_version(str(path))

    assert version_for('release',
                       tag='release-123',
                       node='000',
                      ) == ('PyPy', 'release-123', '000')
    assert version_for('somebranch',
                       node='000',
                       branch='something',
                      ) == ('PyPy', 'something', '000')


def test_get_repo_version_info():
    assert get_repo_version_info(None)
    assert get_repo_version_info(os.devnull) == ('PyPy', '?', '?')
    assert get_repo_version_info(sys.executable) == ('PyPy', '?', '?')
