#!/usr/bin/env python3

"""
Download https://buildbot.pypy.org/pypy/versions.json and parse it
- all the files should be valid
- the other fields should have valid values
- the pypy_version should be in the repo tags
"""

import json
from urllib import request, error

pypy_versions = {'7.3.3': {'python_version': ['3.7.9', '3.6.12', '2.7.18'],
                           'date': '2020-11-21',
                          },
                 '7.3.2': {'python_version': ['3.7.9', '3.6.9', '2.7.13'],
                           'date': '2020-09-25',
                          },
                'nightly': {'python_version': ['2.7', '3.6', '3.7']},
                }
arches = ['aarch64', 'i686', 'x64', 'x86', 'darwin', 's390x']
platforms = ['linux', 'win32', 'darwin']


def assert_equal(a, b):
    if a != b:
        raise ValueError(f"'{a}' != '{b}'")

def assert_in(a, b):
    if a not in b:
        raise ValueError(f"'{a}' not in '{b}'")

response = request.urlopen('https://buildbot.pypy.org/pypy/versions.json')
assert_equal(response.getcode(), 200)
data = json.loads(response.read())



for d in data:
    assert_in(d['pypy_version'], pypy_versions)
    v = pypy_versions[d['pypy_version']]
    assert_in(d['python_version'], v['python_version'])
    if 'date' in d:
        assert_equal(d['date'], v['date'])
    for f in d['files']:
        assert_in(f['filename'], f['download_url'])
        assert_in(f['arch'], arches)
        assert_in(f['platform'], platforms)
        try:
            r = request.urlopen(f['download_url'])
        except error.HTTPError as e:
            raise ValueError(f"could not open {f['download_url']}") from None
        assert_equal(r.getcode(), 200)
        
