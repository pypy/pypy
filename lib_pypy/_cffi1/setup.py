from distutils.core import setup
from distutils.extension import Extension
setup(name='realize_c_type',
      ext_modules=[Extension(name='realize_c_type',
                             sources=['realize_c_type.c',
                                      'parse_c_type.c'])])
