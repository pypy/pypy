"""Test comparisons of Exceptions in except clauses.

New for PyPy - Could be incorporated into CPython regression tests.
"""

class AppTestExceptionComp: 

    def test_exception(self):
        try:
            raise TypeError, "nothing"
        except TypeError:
            pass
        except:
            self.fail("Identical exceptions do not match.") 

    def test_exceptionfail(self):
        try:
            raise TypeError, "nothing"
        except KeyError:
            self.fail("Different exceptions match.")
        except TypeError:
            pass
        except:
            self.fail("Unanticipated value for exception raise.")
            

    def test_called(self):
        try:
            raise SyntaxError("Invalid")
        except SyntaxError:
            pass
        except:
            self.fail("Instantiated exception does not match parent class.") 

    def test_calledfail(self):
        try:
            raise SyntaxError("Invalid")
        except ZeroDivisionError:
            self.fail("Instantiated exception matches different parent class.") 
        except SyntaxError:
            pass
        except:
            self.fail("Unanticpated value for exception raise.")
            
        
    def test_userclass(self):
        class UserExcept(Exception):
            pass
        try:
            raise UserExcept, "nothing"
        except UserExcept:
            pass
        except:
            self.fail("User defined class exceptions do not match.") 
            
    def test_subclass(self):
        try:
            raise KeyError("key")
        except LookupError:
            pass
        except:
            self.fail("Exception does not match parent class.") 

    def test_deepsubclass(self):
        try:
            raise FloatingPointError("1.2r")
        except Exception:
            pass
        except:
            self.fail("Exception does not match grandparent class.") 

    def test_tuple(self):
        try:
            raise ArithmeticError("2+jack")
        except (ZeroDivisionError, ArithmeticError):
            pass
        except:
            self.fail("Exception does not match self in tuple.") 

    def test_parenttuple(self):
        try:
            raise ZeroDivisionError("0")
        except (StandardError, SystemExit):
            pass
        except:
            self.fail("Exception does not match parent in tuple.") 

    def test_nestedtuples(self):
        try:
            raise AssertionError("0")
        except (SystemExit, (KeyboardInterrupt, AssertionError)):
            pass
        except:
            self.fail("Exception does not match self in nested tuple.") 

    def test_deeptuples(self):
        try:
            raise IOError
        except (FloatingPointError,(OSError,
                                    (SyntaxError,IOError,ZeroDivisionError)),
                (MemoryError, NotImplementedError)):
            pass
        except:
            self.fail("Exception does not match self in deeply nested tuple.")
