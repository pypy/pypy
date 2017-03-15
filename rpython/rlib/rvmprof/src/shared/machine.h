#pragma once

/**
 * What is the usual word size of the processor? 64bit? 32bit?
 */
int vmp_machine_bits(void);

/**
 * Return the human readable name of the operating system.
 */
const char * vmp_machine_os_name(void);

