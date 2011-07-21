namespace fragile {

class no_such_class;

class A {
public:
    virtual int check() { return (int)'A'; }
};

class B {
public:
    virtual int check() { return (int)'B'; }
    no_such_class* gime_no_such() { return 0; }
};

class C {
public:
    virtual int check() { return (int)'C'; }
    void use_no_such(no_such_class*) {}
};

class D {
public:
    virtual int check() { return (int)'D'; }
    void overload() {}
    void overload(no_such_class*) {}
    void overload(char, int i = 0) {}  // Reflex requires a named arg
    void overload(int, no_such_class* p = 0) {}
};

class E {
public:
    E() : m_pp_no_such(0), m_pp_a(0) {}

    virtual int check() { return (int)'E'; }
    void overload(no_such_class**) {}

    no_such_class** m_pp_no_such;
    A** m_pp_a;
};

} // namespace fragile
