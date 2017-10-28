//===========================================================================
class MyTemplatedMethodClass {         // template methods
public:
    long get_size();      // to get around bug in genreflex
    template<class B> long get_size();

    long get_char_size();
    long get_int_size();
    long get_long_size();
    long get_float_size();
    long get_double_size();

    long get_self_size();

private:
    double m_data[3];
};

template<class B>
inline long MyTemplatedMethodClass::get_size() {
    return sizeof(B);
}

//
typedef MyTemplatedMethodClass MyTMCTypedef_t;

// explicit instantiation
template long MyTemplatedMethodClass::get_size<char>();
template long MyTemplatedMethodClass::get_size<int>();

// "lying" specialization
template<>
inline long MyTemplatedMethodClass::get_size<long>() {
    return 42;
}
