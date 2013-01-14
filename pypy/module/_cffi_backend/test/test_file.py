import urllib2, py


def test_same_file():
    # '_backend_test_c.py' is a copy of 'c/test_c.py' from the CFFI repo,
    # with the header lines (up to '# _____') stripped.
    url = 'https://bitbucket.org/cffi/cffi/raw/default/c/test_c.py'
    source = urllib2.urlopen(url).read()
    #
    dest = py.path.local(__file__).join('..', '_backend_test_c.py').read()
    #
    source = source[source.index('# _____________'):]
    if source.strip() != dest.strip():
        raise AssertionError(
            "Update test/_backend_test_c.py by copying it from "
            "https://bitbucket.org/cffi/cffi/raw/default/c/test_c.py "
            "and killing the import lines at the start")
