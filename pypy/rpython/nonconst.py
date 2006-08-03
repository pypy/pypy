
""" simple non-constant constant. Ie constant which does not get annotated as constant
"""

from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.annotation.bookkeeper import getbookkeeper

class NonConstant(object):
    def __init__(self, _constant):
        self.constant = _constant

class EntryNonConstant(ExtRegistryEntry):
    _about_ = NonConstant
    
    def compute_result_annotation(self, arg):
        return getbookkeeper().annotation_from_example(arg.const)
