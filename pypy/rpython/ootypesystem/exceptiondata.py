from pypy.rpython.exceptiondata import AbstractExceptionData

class ExceptionData(AbstractExceptionData):
    """Public information for the code generators to help with exceptions."""

    def make_helpers(self, rtyper):
        pass

