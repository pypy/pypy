#!/usr/bin/env python2.7
import os, os.path, sys, importlib, os, vcstools, sh

SCRIPT_PATH = os.path.abspath(__file__)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)
DEPS_DIR = os.path.join(SCRIPT_DIR, "deps")
UNIPY_BIN_DIR = os.path.join(SCRIPT_DIR, "pypy", "goal")
UNI_SYMLINK_DIR = os.path.join(SCRIPT_DIR, "lib_pypy")

PYRO_VCS = "hg"
PYRO_VERSION = "unipycation" # branch
PYRO_REPO="ssh://hg@bitbucket.org/cfbolz/pyrolog-unipycation"
PYRO_DIR = os.path.join(DEPS_DIR, "pyrolog")

SHARED_VCS = "git"
SHARED_VERSION = "master"
SHARED_REPO = "git@bitbucket.org:softdevteam/unipycation-shared.git"
DEFAULT_SHARED_DIR = os.path.join(DEPS_DIR, "unipycation-shared")

PATHS_CONF = os.path.join(SCRIPT_DIR, "paths.conf")
ENV_SH = os.path.join(SCRIPT_DIR, "env.sh")

#
# FETCH
#

def fetch_deps(with_shared=True):
    if not os.path.exists(DEPS_DIR):
        os.mkdir(DEPS_DIR)

    if with_shared: fetch_shared()
    fetch_pyro()

# used only for standalone bootstrap
def fetch_shared():
    vcs = vcstools.get_vcs_client(SHARED_VCS, DEFAULT_SHARED_DIR)
    if not os.path.exists(DEFAULT_SHARED_DIR):
        print("Cloning fresh unipycation-shared: version=%s" % SHARED_VERSION)
        vcs.checkout(SHARED_REPO, version=SHARED_VERSION)
    else:
        print("Updating existing unipycation-shared to version: %s"
                % SHARED_VERSION)
        vcs.update(version=SHARED_VERSION, force_fetch=True)

def fetch_pyro():
    vcs = vcstools.get_vcs_client(PYRO_VCS, PYRO_DIR)
    if not os.path.exists(PYRO_DIR):
        print("Cloning pyrolog: version=%s" % PYRO_VERSION)
        vcs.checkout(PYRO_REPO, version=PYRO_VERSION)
    else:
        print("Updating existing pyrolog to version: %s" % PYRO_VERSION)
        vcs.update(version=PYRO_VERSION)

#
# BUILD
#

# translate
def build_unipycation(shared_dir):
    print("Translating unipycation...")
    sh.Command(sys.executable)(
            os.path.join(shared_dir, "translate_unipycation.py"),
            _out=sys.stdout, _err=sys.stderr)
    sh.mv(os.path.join(UNIPY_BIN_DIR, "pypy-c"),
            os.path.join(UNIPY_BIN_DIR, "unipycation"))

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
    if os.path.islink(dest):
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

    if target in ["build", "all"]:
        build_unipycation(shared_dir)

def usage():
    print("\nUsage:")
    print("  bootstrap.py target [unipycation_shared_path]")
    print("\nIf no path specified, will clone afresh")
    print("\nValid targets: fetch, build, all.")
    sys.exit(666)

if __name__ == "__main__":

    try:
        shared_arg = sys.argv[2]
    except IndexError:
        shared_arg = None

    try:
        target = sys.argv[1]
    except IndexError:
        usage()

    if target not in ["fetch", "build", "configure", "all"]:
        print("Bad target")
        usage()

    if shared_arg is not None:
        bootstrap(target, shared_arg)
    else:
        bootstrap(target)
