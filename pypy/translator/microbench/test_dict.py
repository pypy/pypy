
iterations = 500000
d_x = {}
def test_dict_setitem1():
    d = {}
    for x in range(iterations):
        d[x] = None
        d[x] = None
        d[x] = None
        d[x] = None


def test_dict_setitem2():
    for x in range(iterations):
        d_x[x] = None
        d_x[x] = None
        d_x[x] = None
        d_x[x] = None

def test_dict_creation_mode1():
    for x in range(iterations):
        d = {}
        d[1] = "a"

def test_dict_creation_mode2():
    for x in range(iterations):
        d = {1: "b"}

def test_dict_creation_mode3():
    for x in range(iterations):
        d = {}
        d = {}
        d = {}
        {}


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

# class and attrs

class NewStyle(object):
    def __init__(self):
        self.a = 3
        self.b = 4
    def f(self):
        pass
    def g(self):
        pass


def test_dict_class_dict_getmethod():
    a = NewStyle()
    for x in range(iterations):
        a.f 
        a.f 
        a.f 
        a.f 
        
def test_dict_instance_getattr_instance_dict():
    a = NewStyle()
    for x in range(iterations):
        a.a 
        a.b 
        a.a 
        a.b 

def test_dict_instance_setattr_instance_dict():
    a = NewStyle()
    for x in range(iterations):
        a.a = 3
        a.b = 4
        a.a = 3
        a.b = 4

def test_dict_instance_setnewattr_instance_dict():
    a = NewStyle()
    for x in range(iterations):
        a.c = 3
        a.d = 4
        a.e = 5
        a.f = 6

# old-style

class OldStyle:
    def __init__(self):
        self.a = 3
        self.b = 4
    def f(self):
        pass
    def g(self):
        pass


def test_dict_class_dict_getmethod_old_style():
    a = OldStyle()
    for x in range(iterations):
        a.f 
        a.f 
        a.f 
        a.f 
        
def test_dict_instance_getattr_instance_dict_old_style():
    a = OldStyle()
    for x in range(iterations):
        a.a 
        a.b 
        a.a 
        a.b 

def test_dict_instance_setattr_instance_dict_old_style():
    a = OldStyle()
    for x in range(iterations):
        a.a = 3
        a.b = 4
        a.a = 3
        a.b = 4

def test_dict_instance_setnewattr_instance_dict_old_style():
    a = OldStyle()
    for x in range(iterations):
        a.c = 3
        a.d = 4
        a.e = 5
        a.f = 6
