
iterations = 100000
def test_dict_setitem():
    d = {}
    for x in range(iterations):
        d[x] = None
        d[x] = None
        d[x] = None
        d[x] = None

d = {}
for x in range(iterations):
    d[x] = x

def test_dict_getitem():
    for x in range(iterations):
        y = d[x]
        y = d[x]
        y = d[x]
        y = d[x]

def test_dict_raw_range():
    for x in range(iterations):
        pass

class A:
    def __init__(self):
        self.a = 3
        self.b = 4
    def f(self):
        pass
    def g(self):
        pass


def test_dict_class_dict_getmethod():
    a = A()
    for x in range(iterations):
        a.f 
        a.f 
        a.f 
        a.f 
        
def test_dict_instance_getattr_instance_dict():
    a = A()
    for x in range(iterations):
        a.a 
        a.b 
        a.a 
        a.b 

def test_dict_instance_setattr_instance_dict():
    a = A()
    for x in range(iterations):
        a.a = 3
        a.b = 4
        a.a = 3
        a.b = 4

def test_dict_instance_setnewattr_instance_dict():
    a = A()
    for x in range(iterations):
        a.c = 3
        a.d = 4
        a.e = 5
        a.f = 6
