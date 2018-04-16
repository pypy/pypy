import py
import subprocess

here = py.path.local('.')
moddir = here / 'pypy' / 'module'
blacklist = ['test_lib_pypy']
modules = [path for path in moddir.listdir() if
    path.isdir() and (path / '__init__.py').isfile() and
        path.basename not in blacklist]


def doit(p):
   if not (p / '__init__.py').isfile():
       return
   init = (p / '__init__.py').relto(here)
   target = (p / 'moduledef.py').relto(here)
   subprocess.call(['hg', 'mv', init, target])
   subprocess.call(['touch', init])
   subprocess.call(['hg', 'add', init])

for p in modules:
    doit(p)
