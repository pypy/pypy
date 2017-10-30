#include "stltypes.h"


//- class with lots of std::string handling
stringy_class::stringy_class(const char* s) : m_string(s) {}

std::string stringy_class::get_string1() { return m_string; }
void stringy_class::get_string2(std::string& s) { s = m_string; }

void stringy_class::set_string1(const std::string& s) { m_string = s; }
void stringy_class::set_string2(std::string s) { m_string = s; }
