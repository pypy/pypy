from os.path import *
import py

pytest_plugins = [
    'rpython.tool.pytest.bugfixes',
    'rpython.tool.pytest.expecttest',
    'rpython.tool.pytest.leakfinder',
    'rpython.tool.pytest.platform',
    'rpython.tool.pytest.viewerplugin',
]

cdir = realpath(join(dirname(__file__), 'translator', 'c'))
cache_dir = realpath(join(dirname(__file__), '_cache'))


