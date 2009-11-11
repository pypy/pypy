import py

from pypy.config.makerestdoc import register_config_role 
docdir = py.path.local(__file__).dirpath()

pytest_plugins = "pytest_restdoc"

def pytest_addoption(parser):
    group = parser.getgroup("pypy-doc options")
    group.addoption('--pypy-doctests', action="store_true",
           dest="pypy_doctests", default=False, 
           help="enable doctests in .txt files")
    group.addoption('--generate-redirections',
        action="store_true", dest="generateredirections",
        default=True, help="Generate redirecting HTML files")

def pytest_configure(config):
    register_config_role(docdir)

def pytest_doctest_prepare_content(content):
    if not py.test.config.getvalue("pypy_doctests"):
        py.test.skip("specify --pypy-doctests to run doctests")
    l = []
    for line in content.split("\n"):
        if line.find('>>>>') != -1: 
            line = "" 
        l.append(line) 
    return "\n".join(l) 

