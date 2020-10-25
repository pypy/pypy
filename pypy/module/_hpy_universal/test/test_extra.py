"""
This file contains extra hpy tests in addition to the ones which are in
test/_vendored.

The idea is that during development, sometimes it is useful to write tests
about certain specific features/code paths/corner cases which are not covered
(yet!) by the official hpy tests, so this is a place to collect them.

Once the development phase is finished, please move these tests to the main
hpy repo, and then copy them back here via ./update_vendored.sh.
"""

from pypy.module._hpy_universal.test._vendored.support import HPyTest

class TestExtra(HPyTest):
    pass

    """
    Additional tests to write:

      - check the .readonly field of HPyDef_MEMBER (and also the corresponding
        flag for the PyMemberDef cpy_compat case)


    ListBuilder:

      - in the C code there is logic to delay the MemoryError until we call
        ListBuilder_Build, but it is not tested

      - ListBuilder_Cancel is not tested

    """


class TestExtraCPythonCompatibility(HPyTest):
    # these tests are run with cpyext support, see conftest.py
    pass
