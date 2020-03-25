import pytest
from pypy.module._hpy_universal._vendored.test import test_argparse as _t
from .support import HPyAppTest


class AppTestParseItem(HPyAppTest, _t.TestParseItem):
    spaceconfig = {'usemodules': ['_hpy_universal']}
    w_make_parse_item = _t.TestParseItem.make_parse_item

class AppTestArgParse(HPyAppTest, _t.TestArgParse):
    spaceconfig = {'usemodules': ['_hpy_universal']}
    w_make_two_arg_add = _t.TestArgParse.make_two_arg_add

class AppTestArgParseKeywords(HPyAppTest, _t.TestArgParseKeywords):
    spaceconfig = {'usemodules': ['_hpy_universal']}
    w_make_two_arg_add = _t.TestArgParseKeywords.make_two_arg_add
