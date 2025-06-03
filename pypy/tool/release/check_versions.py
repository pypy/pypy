#!/usr/bin/env python3

"""
Verify the versions.json file that describes the valid downloads.
- all the files should be valid
- the other fields should have valid values
- the pypy_version should be in the repo tags

By default will download https://buildbot.pypy.org/pypy/versions.json parse it, and
check against the files in https://downloads.python.org/pypy/
Can be run as check_versions.py <filename>, in which case it will check the files in
https://buildbot.pypy.org/mirror/
"""

import json
from urllib import request, error
import sys
import time


def assert_equal(a, b):
    if a != b:
        raise ValueError(f"'{a}' != '{b}'")


def assert_different(a, b):
    if a == b:
        raise ValueError(f"'{a}' == '{b}'")


def assert_in(a, b):
    if a not in b:
        raise ValueError(f"'{a}' not in '{b}'")


pypy_versions = {
                 '7.3.19': {'python_version': ['3.11.11', '3.10.16', '2.7.18'],
                           'date': '2025-02-26',
                          },
                 '7.3.18': {'python_version': ['3.11.11', '3.10.16', '2.7.18'],
                           'date': '2025-02-06',
                          },
                 '7.3.17': {'python_version': ['3.10.14', '2.7.18'],
                           'date': '2024-08-28',
                          },
                 '7.3.16': {'python_version': ['3.10.14', '3.9.19', '2.7.18'],
                           'date': '2024-04-24',
                          },
                 '7.3.15': {'python_version': ['3.10.13', '3.9.18', '2.7.18'],
                           'date': '2024-01-15',
                          },
                 '7.3.14': {'python_version': ['3.10.13', '3.9.18', '2.7.18'],
                           'date': '2023-12-25',
                          },
                 '7.3.13': {'python_version': ['3.10.13', '3.9.18', '2.7.18'],
                           'date': '2023-09-29',
                          },
                 '7.3.12': {'python_version': ['3.10.12', '3.9.17', '2.7.18'],
                           'date': '2023-06-16',
                          },
                 '7.3.12rc2': {'python_version': ['3.10.11', '3.9.16', '2.7.18'],
                           'date': '2023-05-28',
                          },
                 '7.3.12rc1': {'python_version': ['3.10.9', '3.9.16', '2.7.18'],
                           'date': '2023-05-13',
                          },
                 '7.3.11': {'python_version': ['3.9.16', '3.8.16', '2.7.18'],
                           'date': '2022-12-29',
                          },
                 '7.3.10': {'python_version': ['3.9.15', '3.8.15', '2.7.18'],
                           'date': '2022-12-06',
                          },
                 '7.3.10rc3': {'python_version': ['3.9.15', '3.8.15', '2.7.18'],
                           'date': '2022-11-24',
                          },
                 '7.3.9': {'python_version': ['3.9.12', '3.8.13', '3.7.13', '2.7.18'],
                           'date': '2022-03-30',
                          },
                 '7.3.8': {'python_version': ['3.9.10', '3.8.12', '3.7.12', '2.7.18'],
                           'date': '2022-02-19',
                          },
                 '7.3.8rc2': {'python_version': ['3.9.10', '3.8.12', '3.7.12', '2.7.18'],
                           'date': '2022-02-11',
                          },
                 '7.3.8rc1': {'python_version': ['3.9.10', '3.8.12', '3.7.12', '2.7.18'],
                           'date': '2022-01-26',
                          },
                 '7.3.7': {'python_version': ['3.8.12', '3.7.12'],
                           'date': '2021-10-25',
                          },
                 '7.3.6': {'python_version': ['3.8.12', '3.7.12', '2.7.18'],
                           'date': '2021-10-17',
                          },
                 '7.3.6rc3': {'python_version': ['3.8.12', '3.7.12', '2.7.18'],
                           'date': '2021-10-12',
                          },
                 '7.3.6rc2': {'python_version': ['3.8.12', '3.7.12', '2.7.18'],
                           'date': '2021-10-06',
                          },
                 '7.3.6rc1': {'python_version': ['3.8.12', '3.7.12', '2.7.18'],
                           'date': '2021-09-13',
                          },
                 '7.3.5': {'python_version': ['3.7.10', '2.7.18'],
                           'date': '2021-05-23',
                          },
                 '7.3.5rc3': {'python_version': ['3.7.10', '2.7.18'],
                           'date': '2021-05-19',
                          },
                 '7.3.5rc2': {'python_version': ['3.7.10', '2.7.18'],
                           'date': '2021-05-05',
                          },
                 '7.3.5rc1': {'python_version': ['3.7.10', '2.7.18'],
                           'date': '2021-05-02',
                          },
                 '7.3.4': {'python_version': ['3.7.10', '2.7.18'],
                           'date': '2021-04-08',
                          },
                 '7.3.4rc2': {'python_version': ['3.7.10', '2.7.18'],
                           'date': '2021-04-04',
                          },
                 '7.3.4rc1': {'python_version': ['3.7.10', '2.7.18'],
                           'date': '2021-03-19',
                          },
                 '7.3.3': {'python_version': ['3.7.9', '3.6.12', '2.7.18'],
                           'date': '2020-11-21',
                          },
                 '7.3.3rc1': {'python_version': ['3.6.12'],
                           'date': '2020-11-11',
                          },
                 '7.3.2': {'python_version': ['3.7.9', '3.6.9', '2.7.13'],
                           'date': '2020-09-25',
                          },
                'nightly': {'python_version': ['2.7', '3.6', '3.7', '3.8', '3.9', '3.10', '3.11']},
                }


def create_latest_versions(v):
    """Create a dictionary with key of cpython_version and value of the latest
    pypy version for that cpython"""
    ret = {}
    for pypy_ver, vv in v.items():
        if 'rc' in pypy_ver:
            # skip release candidates
            continue
        for pv in vv['python_version']:
            # for nightlies, we rely on python_version being major.minor while
            # for releases python_version is major.minor.patch
            if pv not in ret or (
                    vv['date'] > v[ret[pv]]['date']):
                ret[pv] = pypy_ver
    return ret


latest_pypys = create_latest_versions(pypy_versions)

# arches = ['aarch64', 'i686', 'x64', 'x86', 'darwin', 's390x', 'arm64']
arches = ['aarch64', 'i686', 'x64', 'x86', 'darwin', 'arm64']
platforms = ['linux', 'win32', 'win64', 'darwin']
arch_map={('aarch64', 'linux'): 'aarch64',
          ('i686', 'linux'): 'linux32',
          ('x64', 'linux'): 'linux64',
          ('s390x', 'linux'): 's390x',
          ('x86', 'win32'): 'win32',
          ('x64', 'win64'): 'win64',
          ('x64', 'darwin'): ['macos_x86_64', 'osx64'],
          ('arm64', 'darwin'): ['macos_arm64'],
         }

def check_tags(data):
    # Make sure the top tag appears in https://github/pypy/pypy
    # If this fails, probably forgot to do "git push --tags"
    URL_BASE = "https://github.com/pypy/pypy/releases/tag"
    pypy_newest_version = data[0]['pypy_version']
    for d in data:
        if d['pypy_version'] != pypy_newest_version:
            continue
        py_major, py_minor, py_patch = d['python_version'].split('.')
        tag = f"release-pypy{py_major}.{py_minor}-v{pypy_newest_version}"
        tag_url = f"{URL_BASE}/{tag}"
        try:
            r = request.urlopen(tag_url)
        except error.HTTPError as e:
            raise ValueError(f"could not find {tag}' on github. Does the tag exist (forgotten git push --tags)?") from None
        assert_equal(r.getcode(), 200)

def check_versions(data, url, verbose=0, check_times=True, nightly_only=False):
    for d in data:
        if verbose > 0:
            print(f"checking {d['python_version']} {d['pypy_version']}")
        assert_in(d['pypy_version'], pypy_versions)
        v = pypy_versions[d['pypy_version']]
        assert_in(d['python_version'], v['python_version'])
        if ('rc' in d['pypy_version'] or 'nightly' in d['pypy_version']):
            assert d['stable'] is False
        else:
            assert d['stable'] is True
        if d['pypy_version'] == 'nightly':
            assert d['latest_pypy'] is False
        elif d['latest_pypy'] is True:
            assert_equal(latest_pypys[d['python_version']], d['pypy_version'])
        else:
            try:
                # Make sure there is only one latest version
                assert_different(latest_pypys[d['python_version']], d['pypy_version'])
            except KeyError:
                assert 'rc' in d['pypy_version']
        if 'date' in d:
            assert_equal(d['date'], v['date'])
        for f in d['files']:
            download_url = f['download_url']
            if verbose > 0:
                print(f'     checking {download_url:<80}', end='')
            if 'rc' not in d['pypy_version']:
                assert_in(f['filename'], download_url)
                assert_in(d['pypy_version'], download_url)
            if f['arch'] not in ('s390x',):
                # We dropped s390x uploads, don't bother checking historically
                assert_in(f['arch'], arches)
                assert_in(f['platform'], platforms)
                arch_plat = arch_map[(f['arch'], f['platform'])]
                py_ver = '.'.join(d['python_version'].split('.')[:2])
                if d['pypy_version'] == 'nightly':
                    if f['platform'] == "darwin":
                        if arch_plat[0] not in download_url and arch_plat[1] not in download_url:
                            raise ValueError(f"{arch_plat} not in {download_url}")
                    elif arch_plat == 'linux32':
                        # the nightly builds have a quirk in the linux32 file name
                        arch_plat = 'linux'
                        assert_in(arch_plat, download_url)
                    else:
                        assert_in(arch_plat, download_url)
                    py_ver_tuple = [int(s) for s in py_ver.split('.')]
                    if py_ver == "2.7":
                        py_ver = "main"
                elif f['platform'] == "darwin":
                    if arch_plat[0] not in download_url and arch_plat[1] not in download_url:
                        raise ValueError(f"{arch_plat} not in {download_url}")
                else:
                    assert_in(arch_plat, download_url)
                assert_in(py_ver, download_url)
            if d['pypy_version'] != 'nightly' and nightly_only:
                if verbose > 0:
                    print(f' ok')
                continue
            if url and not d['pypy_version'] == "nightly":
                download_url = '/'.join((url, download_url.rsplit('/', 1)[1]))
            try:
                r = request.urlopen(download_url)
            except error.HTTPError as e:
                raise ValueError(f"could not open '{download_url}', got {e}") from None
            assert_equal(r.getcode(), 200)
            if d['pypy_version'] == 'nightly' and (py_ver_tuple > [3, 10] or py_ver == "main"):
                print('time-check', end='')
                # nightly builds do not have a date entry, use time.time()
                target = time.strftime("%Y-%m-%d")
                # Check that the last modified time is within a week of target
                # The modified time is something like  Mon, 06 Jun 2022 05:41:46
                modified_time_str = ' '.join(r.getheader("Last-Modified").split(' ')[1:4])
                expected_time = time.mktime(time.strptime(target, "%Y-%m-%d"))
                modified_time = time.mktime(time.strptime(modified_time_str, "%d %b %Y"))
                delta_days = abs(expected_time - modified_time) / (60 * 60 * 24)
                if delta_days > 14 and 's390x' not in f['arch']:
                    raise ValueError(f"expected {modified_time_str} to be within 2 weeks of {target}")
                else:
                    print(f" {delta_days} days", end='')
            if verbose > 0:
                print(f' ok')
        if verbose > 0:
            print(f"{d['python_version']} {d['pypy_version']} ok")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        print(f'checking local file "{sys.argv[1]}"')
        with open(sys.argv[1]) as fid:
            data = json.loads(fid.read())
        nightly_only = '--nightly-only' in sys.argv
        check_versions(data, 'https://buildbot.pypy.org/mirror/', verbose=1,
                       nightly_only=nightly_only)
    else:
        print('downloading versions.json')
        response = request.urlopen('https://buildbot.pypy.org/pypy/versions.json')
        assert_equal(response.getcode(), 200)
        data = json.loads(response.read())
        check_versions(data, None, verbose=1)
    check_tags(data)
    print('ok')
