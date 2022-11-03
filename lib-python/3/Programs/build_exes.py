#

import sys
import sysconfig
import setuptools

from distutils.ccompiler import new_compiler

compiler = new_compiler()
compiler.add_include_dir(sysconfig.get_path("include"))
compiler.add_library_dir(sysconfig.get_config_var("installed_platbase") + "/libs")

if sys.platform == "linux":
    compiler.add_library_dir(sysconfig.get_config_var("LIBPL"))
    compiler.add_library_dir(sysconfig.get_config_var("LIBDIR"))

    compiler.add_library(sysconfig.get_config_var("LIBRARY")[3:-2])

def build_exe(sources, exe_name):
    objectFiles = compiler.compile(sources)
    return compiler.link_executable(objectFiles, exe_name)



if __name__ == "__main__":
    import pathlib, os
    mydir = pathlib.Path(__file__).parent
    if len(sys.argv) > 1:
        files = [pathlib.Path(x) for x in sys.argv[1:]]
    else:
        files = list(mydir.glob("*.c"))
    oldir = os.getcwd()
    os.chdir(mydir)
    try:
        for f in files:
            print(build_exe([f.name], f.stem))
    finally:
        os.chdir(oldir)
    
