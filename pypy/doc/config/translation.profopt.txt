Use GCCs profile-guided optimizations. This option specifies the the
arguments with which to call pypy-c (and in general the translated
RPython program) to gather profile data. Example for pypy-c: "-c 'from
richards import main;main(); from test import pystone;
pystone.main()'"
