#ifndef HUMANWILL_NATIVE_H
#define HUMANWILL_NATIVE_H
#include "yyjson.h"
#include <stdbool.h>
#include <stddef.h>
#define LIMIT 262144u
void fail(const char *code);
void *mem(size_t size);
void json_cleanup(void);
yyjson_val *parse(const char *data, size_t size);
char *canonical(yyjson_val *value);
yyjson_val *get(yyjson_val *value, const char *key);
bool isstr(yyjson_val *value, const char *text);
bool equal(yyjson_val *a, yyjson_val *b);
double number(yyjson_val *value);
size_t codepoints(const char *s, size_t length);
bool nonspace(const char *s, size_t length);
bool validate(yyjson_val *schema, yyjson_val *value);
#endif
