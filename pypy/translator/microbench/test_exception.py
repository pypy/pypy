
# some of these tests might be identical and can be removed

N = int(2**19 - 1)

class MyException(Exception):
    pass

class MyException1(Exception):
    pass

class MyException2(Exception):
    pass

class MyException3(Exception):
    pass

#
def test_try_except():
    c = 0
    n = N
    while c < n:
        try:
            pass
        except:
            pass
        c += 1

#
def test_try_except_else():
    c = 0
    n = N
    while c < n:
        try:
            pass
        except:
            pass
        else:
            pass
        c += 1

#
def test_try_except_finally():
    c = 0
    n = N
    while c < n:
        try:
            pass
        finally:
            pass
        c += 1

#
def test_instantiate_builtin_exception():
    c = 0
    n = N
    while c < n:
        IndexError()
        IndexError()
        IndexError()
        IndexError()
        IndexError()
        c += 1

#
def test_instantiate_user_exception():
    c = 0
    n = N
    while c < n:
        MyException()
        MyException()
        MyException()
        MyException()
        MyException()
        c += 1

#
def test_raise_builtin_exception():
    c = 0
    n = N
    e = IndexError()
    while c < n:
        try:
            raise e
        except:
            pass
        c += 1

#
def test_raise_user_exception():
    c = 0
    n = N
    e = MyException()
    while c < n:
        try:
            raise e
        except:
            pass
        c += 1

#
def test_except_specific_builtin_exception():
    c = 0
    n = N
    e = IndexError()
    while c < n:
        try:
            raise e
        except ValueError:
            pass
        except:
            pass
        c += 1

#
def test_except_multiple_builtin_exception():
    c = 0
    n = N
    e = IndexError()
    while c < n:
        try:
            raise e
        except (ValueError, OverflowError, ZeroDivisionError):
            pass
        except:
            pass
        c += 1

#
def test_except_specific_user_exception():
    c = 0
    n = N
    e = MyException()
    while c < n:
        try:
            raise e
        except MyException1:
            pass
        except:
            pass
        c += 1

#
def test_except_multiple_user_exception():
    c = 0
    n = N
    e = MyException()
    while c < n:
        try:
            raise e
        except (MyException1, MyException2, MyException3):
            pass
        except:
            pass
        c += 1

#
def test_reraise():
    c = 0
    n = N
    e = IndexError()
    while c < n:
        try:
            try:
                raise e
            except:
                raise
        except:
            pass
        c += 1
