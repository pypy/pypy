import _imp
import os
from distutils.spawn import find_executable

so_ext = _imp.extension_suffixes()[0]

build_time_vars = {
    "EXT_SUFFIX": so_ext,
    "SHLIB_SUFFIX": so_ext,
    "SOABI": '-'.join(so_ext.split('.')[1].split('-')[:2]),
    "SO": so_ext  # deprecated in Python 3, for backward compatibility
}

cc_compiler_path = os.path.realpath(find_executable("cc"))
cc_compiler = os.path.basename(cc_compiler_path)
build_time_vars["CC"] = cc_compiler
if "gcc" in cc_compiler or "g++" in cc_compiler:
    # If we used the gnu compiler, we can safely assume we are using the gnu
    # linker
    build_time_vars["GNULD"] = "yes"
