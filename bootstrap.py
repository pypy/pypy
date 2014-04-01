#!/usr/bin/env python2.7
import os, os.path, sys

SCRIPT_PATH = os.path.abspath(__file__)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)
DEPS_DIR = os.path.join(SCRIPT_DIR, "deps")
UNIPY_BIN_DIR = os.path.join(SCRIPT_DIR, "pypy", "goal")
UNI_SYMLINK_DIR = os.path.join(SCRIPT_DIR, "lib_pypy")

PYRO_REPO="ssh://hg@bitbucket.org/cfbolz/pyrolog-unipycation"
PYRO_DIR = os.path.join(DEPS_DIR, "pyrolog")

SHARED_REPO = "git@bitbucket.org:softdevteam/unipycation-shared.git"
DEFAULT_SHARED_DIR = os.path.join(DEPS_DIR, "unipycation-shared")

PATHS_CONF = os.path.join(SCRIPT_DIR, "paths.conf")
ENV_SH = os.path.join(SCRIPT_DIR, "env.sh")

try:
    import pip
except ImportError:
    raise ImportError("Please install pip")

# list of (package_name, import_name)
REQUIRED = [ ("sh", "sh") ]
for (pkg, mod) in REQUIRED:
    try:
        exec("import %s" % mod)
    except ImportError:
        print("Installing %s..." % pkg)
        pip.main(['install', '--user', pkg])
        exec("import %s" % mod) # should pass this time

#
# FETCH
#

def fetch_deps(with_shared=True):
    if not os.path.exists(DEPS_DIR):
        os.mkdir(DEPS_DIR)

    if with_shared: fetch_shared()
    fetch_pyro()

def fetch_shared():
    if not os.path.exists(DEFAULT_SHARED_DIR):
        print("Cloning fresh unipycation-shared...")
        sh.git('clone', SHARED_REPO, DEFAULT_SHARED_DIR,
                _out=sys.stdout, _err=sys.stderr)
    else:
        print("Updating existing unipycation-shared...")
        os.chdir(DEFAULT_SHARED_DIR)
        sh.git("pull")

def fetch_pyro():
    if not os.path.exists(PYRO_DIR):
        print("Cloning pyrolog...")
        os.chdir(DEPS_DIR)
        sh.hg("clone", "-u", "unipycation", PYRO_REPO, PYRO_DIR,
                _out=sys.stdout, _err=sys.stderr)
    else:
        print("Updating pyrolog...")
        os.chdir(PYRO_DIR)
        sh.hg("pull", "-u", _out=sys.stdout, _err=sys.stderr)

#
# CONFIGURE
#

def configure(shared_dir=DEFAULT_SHARED_DIR):
    gen_env_sh(shared_dir)
    gen_uni_symlink(shared_dir)

def gen_env_sh(shared_dir):
    print("Generating env.sh...")
    with open(ENV_SH, "w") as f:
        f.write("#!/bin/sh\n")
        f.write("export PYTHONPATH=${PYTHONPATH}:%s:%s\n" % (PYRO_DIR, shared_dir))
        f.write("export PATH=%s:${PATH}\n" % UNIPY_BIN_DIR)
        f.write("alias pypytest='%s %s'\n" %
                (sys.executable, os.path.join(SCRIPT_DIR, "pytest.py")))

        cc=""
        if sys.platform.startswith("openbsd"):
            cc="CC=egcc"

        f.write("alias rpython='%s %s %s'\n" %
                (cc, sys.executable,
                os.path.join(SCRIPT_DIR, "rpython", "bin", "rpython")))

def force_symlink(src, dest):
    if os.path.exists(dest) or os.path.islink(dest):
        os.unlink(dest)
    os.symlink(src, dest)

def gen_uni_symlink(shared_dir):
    print("Generating uni.py symlink...")
    uni_py_path = os.path.join(shared_dir, "unipycation_shared", "uni.py")
    target_path = os.path.join(UNI_SYMLINK_DIR, "uni.py")

    force_symlink(uni_py_path, target_path)

    # Remove old bytecode if there is one
    pyc_path = target_path + "c"
    try:
        os.unlink(pyc_path)
    except OSError:
        pass

#
# MAIN
#
def bootstrap(target, shared_dir=None):
    if shared_dir is None:
        with_shared = True
        shared_dir = DEFAULT_SHARED_DIR
    else:
        with_shared = False
        shared_dir = os.path.abspath(shared_dir)

    if target in ["fetch", "all"]:
        fetch_deps(with_shared)

    # happens in all targets
    configure(shared_dir)

    # XXX actually translate
    if target in ["build", "all"]:
        print("""
        **************************************************************
        *** NOTE: This bootstrapper will not translate unipycation ***
        **************************************************************

        To translate, run translate_unipycation.py.

        Note that OpenBSD users will need to install a newish GCC from packages.

        Once you are translated, source env.sh and run 'pypy-c'.
        """)

def usage():
    print("\nUsage:")
    print("  bootstrap.py target [unipycation_shared_path]")
    print("\nIf no path specified, will clone afresh")
    print("\nValid targets: fetch, build, all.")
    sys.exit(666)

if __name__ == "__main__":

    try:
        shared_arg = sys.argv[2]
    except KeyError:
        shared_arg = None

    try:
        target = sys.argv[1]
    except KeyError:
        usage()

    if target not in ["fetch", "build", "configure", "all"]:
        print("Bad target")
        usage()

    if shared_arg is not None:
        bootstrap(target, shared_arg)
    else:
        bootstrap(target)
