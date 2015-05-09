from distutils.core import setup
from distutils.extension import Extension
setup(name='manual',
      ext_modules=[Extension(name='manual',
                             sources=['manual.c'])])
