#include <list>
#include <map>
#include <string>
#include <vector>

#define STLTYPES_EXPLICIT_INSTANTIATION_DECL(STLTYPE, TTYPE)                    \
extern template class std::STLTYPE< TTYPE >;                                    \
extern template class __gnu_cxx::__normal_iterator<TTYPE*, std::STLTYPE< TTYPE > >;\
extern template class __gnu_cxx::__normal_iterator<const TTYPE*, std::STLTYPE< TTYPE > >;\
namespace __gnu_cxx {                                                           \
extern template bool operator==(const std::STLTYPE< TTYPE >::iterator&,         \
                         const std::STLTYPE< TTYPE >::iterator&);               \
extern template bool operator!=(const std::STLTYPE< TTYPE >::iterator&,         \
                         const std::STLTYPE< TTYPE >::iterator&);               \
}


//- basic example class
class just_a_class {
public:
    int m_i;
};


//- explicit instantiations of used types
STLTYPES_EXPLICIT_INSTANTIATION_DECL(vector, int)
STLTYPES_EXPLICIT_INSTANTIATION_DECL(vector, just_a_class)


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
