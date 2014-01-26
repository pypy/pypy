"""
Code for annotating low-level thingies.
"""
from rpython.annotator.model import SomeObject

class SomeAddress(SomeObject):
    immutable = True

    def can_be_none(self):
        return False

    def is_null_address(self):
        return self.is_immutable_constant() and not self.const

class SomeTypedAddressAccess(SomeObject):
    """This class is used to annotate the intermediate value that
    appears in expressions of the form:
    addr.signed[offset] and addr.signed[offset] = value
    """

    def __init__(self, type):
        self.type = type

    def can_be_none(self):
        return False

