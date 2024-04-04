/*
 * Expat configuration for python. This file is not part of the expat
 * distribution.
 */
#ifndef EXPAT_CONFIG_H
#define EXPAT_CONFIG_H

#define XML_ENABLE_VISIBILITY 1


#ifdef __APPLE__
  #define HAVE_ARC4RANDOM_BUF
#elif defined __GNUC__
  // #define HAVE_GETRANDOM 1
  #define HAVE_SYSCALL_GETRANDOM
  //#define HAVE_GETRANDOM_SYSCALL = 1
  #define HAVE_LINUX_RANDOM_H = 1
  // #define HAVE_SYS_RANDOM_H 1
#elif defined _WIN32
  #define XMLIMPORT __declspec(dllimport)
#else
  #error "unknown platform"
#endif

#ifdef WORDS_BIGENDIAN
#define BYTEORDER 4321
#else
#define BYTEORDER 1234
#endif

#define HAVE_MEMMOVE 1

#define XML_NS 1
#define XML_DTD 1
#define XML_GE 1
#define XML_CONTEXT_BYTES 1024

#endif /* EXPAT_CONFIG_H */
