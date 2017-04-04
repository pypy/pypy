#include <list>
#include <map>
#include <string>
#include <utility>
#include <vector>

//- basic example class
class just_a_class {
public:
    int m_i;
};

//- class with lots of std::string handling
class stringy_class {
public:
   stringy_class(const char* s);

   std::string get_string1();
   void get_string2(std::string& s);

   void set_string1(const std::string& s);
   void set_string2(std::string s);

   std::string m_string;
};

//- class that has an STL-like interface
class no_dict_available;
    
template<class T>
class stl_like_class {
public: 
   no_dict_available* begin() { return 0; }
   no_dict_available* end() { return 0; }
   int size() { return 4; }
   int operator[](int i) { return i; }
   std::string operator[](double) { return "double"; }
   std::string operator[](const std::string&) { return "string"; }
};      


#define STLTYPE_INSTANTIATION(STLTYPE, TTYPE, N)                             \
   std::STLTYPE<TTYPE > STLTYPE##_##N;                                       \
   std::STLTYPE<TTYPE >::iterator STLTYPE##_##N##_i;                         \
   std::STLTYPE<TTYPE >::const_iterator STLTYPE##_##N##_ci

#define STLTYPE_INSTANTIATION2(STLTYPE, TTYPE1, TTYPE2, N)                   \
   std::STLTYPE<TTYPE1, TTYPE2 > STLTYPE##_##N;                              \
   std::pair<TTYPE1, TTYPE2 > STLTYPE##_##N##_p;                             \
   std::pair<const TTYPE1, TTYPE2 > STLTYPE##_##N##_cp;                      \
   std::STLTYPE<TTYPE1, TTYPE2 >::iterator STLTYPE##_##N##_i;                \
   std::STLTYPE<TTYPE1, TTYPE2 >::const_iterator STLTYPE##_##N##_ci


//- instantiations of used STL types
namespace {

    struct _CppyyVectorInstances {

        STLTYPE_INSTANTIATION(vector, int,          1);
        STLTYPE_INSTANTIATION(vector, float,        2);
        STLTYPE_INSTANTIATION(vector, double,       3);
        STLTYPE_INSTANTIATION(vector, just_a_class, 4);

    };

    struct _CppyyListInstances {

        STLTYPE_INSTANTIATION(list, int,    1);
        STLTYPE_INSTANTIATION(list, float,  2);
        STLTYPE_INSTANTIATION(list, double, 3);

    };

    struct _CppyyMapInstances {

#ifndef __CINT__
        STLTYPE_INSTANTIATION2(map, int,         int,           1);
#endif
        STLTYPE_INSTANTIATION2(map, std::string, int,           2);
        STLTYPE_INSTANTIATION2(map, std::string, unsigned int,  3);
        STLTYPE_INSTANTIATION2(map, std::string, unsigned long, 4);

    };

    stl_like_class<int> stlc_1;

} // unnamed namespace

#define STLTYPES_EXPLICIT_INSTANTIATION_DECL_COMPS(STLTYPE, TTYPE)           \
namespace __gnu_cxx {                                                        \
extern template bool operator==(const std::STLTYPE< TTYPE >::iterator&,      \
                         const std::STLTYPE< TTYPE >::iterator&);            \
extern template bool operator!=(const std::STLTYPE< TTYPE >::iterator&,      \
                         const std::STLTYPE< TTYPE >::iterator&);            \
}

// comps for int only to allow testing: normal use of vector is looping over a
// range-checked version of __getitem__
STLTYPES_EXPLICIT_INSTANTIATION_DECL_COMPS(vector, int)
