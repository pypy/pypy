#include "stltypes.h"

#define STLTYPES_EXPLICIT_INSTANTIATION(STLTYPE, TTYPE)                         \
template class std::STLTYPE< TTYPE >;                                           \
template class __gnu_cxx::__normal_iterator<TTYPE*, std::STLTYPE< TTYPE > >;    \
template class __gnu_cxx::__normal_iterator<const TTYPE*, std::STLTYPE< TTYPE > >;\
namespace __gnu_cxx {                                                           \
template bool operator==(const std::STLTYPE< TTYPE >::iterator&,                \
                         const std::STLTYPE< TTYPE >::iterator&);               \
template bool operator!=(const std::STLTYPE< TTYPE >::iterator&,                \
                         const std::STLTYPE< TTYPE >::iterator&);               \
}


//- explicit instantiations of used types
STLTYPES_EXPLICIT_INSTANTIATION(vector, int)
STLTYPES_EXPLICIT_INSTANTIATION(vector, just_a_class)

//- class with lots of std::string handling
stringy_class::stringy_class(const char* s) : m_string(s) {}

std::string stringy_class::get_string1() { return m_string; }
void stringy_class::get_string2(std::string& s) { s = m_string; }

void stringy_class::set_string1(const std::string& s) { m_string = s; }
void stringy_class::set_string2(std::string s) { m_string = s; }
