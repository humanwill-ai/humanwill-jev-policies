#ifndef HUMANWILL_PLATFORM_H
#define HUMANWILL_PLATFORM_H
#include <stddef.h>
int hw_stdio_binary(void);
int hw_sha256(const char *input, size_t length, unsigned char digest[32]);
int hw_ascii_ncasecmp(const char *a, const char *b, size_t length);
#endif
