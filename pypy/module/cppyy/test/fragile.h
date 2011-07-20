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

} // namespace fragile
