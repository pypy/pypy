# Subclasses disutils.command.build_ext,
# replacing it with a Pyrex version that compiles pyx->c
# before calling the original build_ext command.
# July 2002, Graham Fawcett
# Modified by Darrell Gallion <dgallion1@yahoo.com>
# to allow inclusion of .c files along with .pyx files.
# Pyrex is (c) Greg Ewing.

import distutils.command.build_ext
import Pyrex.Compiler.Main
from Pyrex.Compiler.Errors import PyrexError
from distutils.dep_util import newer
import os
import sys

def replace_suffix(path, new_suffix):
    return os.path.splitext(path)[0] + new_suffix

class build_ext (distutils.command.build_ext.build_ext):

  description = "compile Pyrex scripts, then build C/C++ extensions (compile/link to build directory)"

  def finalize_options (self):
    distutils.command.build_ext.build_ext.finalize_options(self)

    # The following hack should no longer be needed.
    if 0:
      # compiling with mingw32 gets an "initializer not a constant" error
      # doesn't appear to happen with MSVC!
      # so if we are compiling with mingw32,
      # switch to C++ mode, to avoid the problem
      if self.compiler == 'mingw32':
        self.swig_cpp = 1

  def swig_sources (self, sources):
    if not self.extensions:
      return

    # collect the names of the source (.pyx) files
    pyx_sources = []
    pyx_sources = [source for source in sources if source.endswith('.pyx')]
    other_sources = [source for source in sources if not source.endswith('.pyx')]

    extension = self.swig_cpp and '.cpp' or '.c'
    for pyx in pyx_sources:
      # should I raise an exception if it doesn't exist?
      if os.path.exists(pyx):
        source = pyx
        #target = source.replace('.pyx', extension)
        target = replace_suffix(source, extension)
        if newer(source, target) or self.force:
          self.pyrex_compile(source)

          if self.swig_cpp:
            # rename .c to .cpp (Pyrex always builds .c ...)
            if os.path.exists(target):
              os.unlink(target)
            #os.rename(source.replace('.pyx', '.c'), target)
            os.rename(replace_suffix(source, '.c'), target)
            # massage the cpp file
            self.c_to_cpp(target)

    return [replace_suffix(src, extension) for src in pyx_sources] + other_sources

  def pyrex_compile(self, source):
    result = Pyrex.Compiler.Main.compile(source)
    if result.num_errors <> 0:
      sys.exit(1)

  def c_to_cpp(self, filename):
    """touch up the Pyrex generated c/cpp files to meet mingw32/distutils requirements."""
    f = open(filename, 'r')
    lines = [line for line in f.readlines() if not line.startswith('staticforward PyTypeObject __pyx_type_')]
    f.close()
    f = open(filename, 'w')
    lines.insert(1, 'extern "C" {\n')
    lines.append('}\n')
    f.write(''.join(lines))
    f.close()
