#include "native.h"
#include <ctype.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Per-invocation bounded arena; no allocations survive process completion. */
#define ARENA_LIMIT (32u * 1024u * 1024u)
static unsigned char *arena;
static size_t used;
static yyjson_doc *documents[32];
static size_t document_count;
void *mem(size_t n) {
  if (n > ARENA_LIMIT - 16)
    fail("payload_limit");
  n = (n + 15) & ~(size_t)15;
  if (n > ARENA_LIMIT - used)
    fail("payload_limit");
  if (!arena && !(arena = calloc(1, ARENA_LIMIT)))
    fail("memory_error");
  void *p = arena + used;
  used += n;
  return p;
}
void json_cleanup(void) {
  for (size_t i = 0; i < document_count; i++)
    yyjson_doc_free(documents[i]);
  free(arena);
  arena = NULL;
  used = document_count = 0;
}
yyjson_val *get(yyjson_val *v, const char *key) {
  return yyjson_obj_get(v, key);
}
bool isstr(yyjson_val *v, const char *s) {
  return yyjson_is_str(v) && yyjson_get_len(v) == strlen(s) &&
         memcmp(yyjson_get_str(v), s, strlen(s)) == 0;
}
static bool raw_integer(yyjson_val *v) {
  const char *s = yyjson_get_raw(v);
  return s && !strpbrk(s, ".eE");
}
double number(yyjson_val *v) {
  return yyjson_is_raw(v) ? strtod(yyjson_get_raw(v), NULL) : NAN;
}
static int keycmp(const void *aa, const void *bb) {
  yyjson_val *a = *(yyjson_val *const *)aa, *b = *(yyjson_val *const *)bb;
  size_t al = yyjson_get_len(a), bl = yyjson_get_len(b);
  int c = memcmp(yyjson_get_str(a), yyjson_get_str(b), al < bl ? al : bl);
  return c ? c : (al > bl) - (al < bl);
}
static yyjson_val **keys(yyjson_val *v) {
  size_t i, n;
  yyjson_val *k, *val;
  yyjson_val **out = mem((yyjson_obj_size(v) + 1) * sizeof(*out));
  yyjson_obj_foreach(v, i, n, k, val) {
    (void)val;
    out[i] = k;
  }
  qsort(out, yyjson_obj_size(v), sizeof(*out), keycmp);
  return out;
}
static void strict(yyjson_val *v, unsigned depth) {
  if (depth > 24)
    fail("malformed_json");
  size_t i, n;
  yyjson_val *k, *x;
  if (yyjson_is_obj(v)) {
    yyjson_val **sorted = keys(v);
    for (i = 1; i < yyjson_obj_size(v); i++)
      if (!keycmp(&sorted[i - 1], &sorted[i]))
        fail("malformed_json");
    yyjson_obj_foreach(v, i, n, k, x) {
      (void)k;
      strict(x, depth + 1);
    }
  } else if (yyjson_is_arr(v)) {
    yyjson_arr_foreach(v, i, n, x) strict(x, depth + 1);
  } else if (yyjson_is_raw(v)) {
    if (raw_integer(v)) {
      if (yyjson_get_len(v) > 4300)
        fail("malformed_json");
    } else if (!isfinite(number(v)))
      fail("malformed_json");
  }
}
yyjson_val *parse(const char *data, size_t n) {
  if (n > LIMIT || document_count == 32)
    fail("payload_limit");
  yyjson_doc *d = yyjson_read(data, n, YYJSON_READ_NUMBER_AS_RAW);
  if (!d)
    fail("malformed_json");
  documents[document_count++] = d;
  yyjson_val *v = yyjson_doc_get_root(d);
  strict(v, 0);
  return v;
}
static uint32_t cp(const unsigned char **p) {
  uint32_t c = *(*p)++;
  unsigned n = c < 128 ? 0 : c < 224 ? 1 : c < 240 ? 2 : 3;
  if (n)
    c &= (1u << (6 - n)) - 1;
  while (n--)
    c = (c << 6) | (*(*p)++ & 63);
  return c;
}
size_t codepoints(const char *s, size_t len) {
  size_t n = 0;
  const unsigned char *p = (const unsigned char *)s, *end = p + len;
  while (p < end) {
    cp(&p);
    n++;
  }
  return n;
}
bool nonspace(const char *s, size_t len) {
  const unsigned char *p = (const unsigned char *)s, *end = p + len;
  while (p < end) {
    uint32_t c = cp(&p);
    bool space = (c >= 9 && c <= 13) || (c >= 28 && c <= 32) || c == 0x85 ||
                 c == 0xa0 || c == 0x1680 || (c >= 0x2000 && c <= 0x200a) ||
                 c == 0x2028 || c == 0x2029 || c == 0x202f || c == 0x205f ||
                 c == 0x3000;
    if (!space)
      return true;
  }
  return false;
}
bool equal(yyjson_val *a, yyjson_val *b) {
  if (!a || !b)
    return a == b;
  if (yyjson_is_raw(a) && yyjson_is_raw(b))
    return strtold(yyjson_get_raw(a), NULL) == strtold(yyjson_get_raw(b), NULL);
  if (yyjson_get_type(a) != yyjson_get_type(b))
    return false;
  if (yyjson_is_str(a))
    return yyjson_get_len(a) == yyjson_get_len(b) &&
           !memcmp(yyjson_get_str(a), yyjson_get_str(b), yyjson_get_len(a));
  if (yyjson_is_bool(a))
    return yyjson_get_bool(a) == yyjson_get_bool(b);
  if (yyjson_is_null(a))
    return true;
  if (yyjson_is_arr(a)) {
    if (yyjson_arr_size(a) != yyjson_arr_size(b))
      return false;
    for (size_t i = 0; i < yyjson_arr_size(a); i++)
      if (!equal(yyjson_arr_get(a, i), yyjson_arr_get(b, i)))
        return false;
    return true;
  }
  if (yyjson_is_obj(a)) {
    if (yyjson_obj_size(a) != yyjson_obj_size(b))
      return false;
    size_t i, n;
    yyjson_val *k, *v;
    yyjson_obj_foreach(
        a, i, n, k,
        v) if (!equal(v, yyjson_obj_getn(b, yyjson_get_str(k),
                                         yyjson_get_len(k)))) return false;
    return true;
  }
  return false;
}
typedef struct {
  char *s;
  size_t n;
} Buffer;
static void append(Buffer *b, const char *s, size_t n) {
  if (n > LIMIT - b->n)
    fail("payload_limit");
  memcpy(b->s + b->n, s, n);
  b->n += n;
  b->s[b->n] = 0;
}
static void put(Buffer *b, const char *s) { append(b, s, strlen(s)); }
static void string(Buffer *b, yyjson_val *v) {
  const unsigned char *p = (const unsigned char *)yyjson_get_str(v),
                      *end = p + yyjson_get_len(v);
  put(b, "\"");
  while (p < end) {
    uint32_t c = cp(&p);
    char x[16];
    switch (c) {
    case '"':
      put(b, "\\\"");
      continue;
    case '\\':
      put(b, "\\\\");
      continue;
    case '\b':
      put(b, "\\b");
      continue;
    case '\f':
      put(b, "\\f");
      continue;
    case '\n':
      put(b, "\\n");
      continue;
    case '\r':
      put(b, "\\r");
      continue;
    case '\t':
      put(b, "\\t");
      continue;
    }
    if (c < 32 || c >= 127) {
      if (c <= 0xffff)
        snprintf(x, sizeof(x), "\\u%04x", c);
      else {
        c -= 0x10000;
        snprintf(x, sizeof(x), "\\u%04x\\u%04x", 0xd800 + (c >> 10),
                 0xdc00 + (c & 1023));
      }
      put(b, x);
    } else {
      char a = (char)c;
      append(b, &a, 1);
    }
  }
  put(b, "\"");
}
static void numeric(Buffer *b, yyjson_val *v) {
  const char *raw = yyjson_get_raw(v);
  if (raw_integer(v)) {
    put(b, !strcmp(raw, "-0") ? "0" : raw);
    return;
  }
  double d = number(v);
  if (!isfinite(d))
    fail("malformed_json");
  yyjson_mut_doc *doc = yyjson_mut_doc_new(NULL);
  if (!doc)
    fail("memory_error");
  yyjson_mut_doc_set_root(doc, yyjson_mut_real(doc, d));
  char *shortest = yyjson_mut_write(doc, 0, NULL);
  yyjson_mut_doc_free(doc);
  if (!shortest)
    fail("memory_error");
  char digits[32];
  int count = 0, point = -1, exponent = 0;
  const char *s = shortest;
  if (*s == '-') {
    put(b, "-");
    s++;
  }
  while (*s && *s != 'e' && *s != 'E') {
    if (*s == '.')
      point = count;
    else
      digits[count++] = *s;
    s++;
  }
  if (point < 0)
    point = count;
  if (*s)
    exponent = atoi(s + 1);
  free(shortest);
  int leading = 0;
  while (leading < count - 1 && digits[leading] == '0')
    leading++;
  int power = point - leading - 1 + exponent;
  memmove(digits, digits + leading, (size_t)(count - leading));
  count -= leading;
  while (count > 1 && digits[count - 1] == '0')
    count--;
  if (d == 0) {
    put(b, "0.0");
    return;
  }
  if (power < -4 || power >= 16) {
    append(b, digits, 1);
    if (count > 1) {
      put(b, ".");
      append(b, digits + 1, (size_t)count - 1);
    }
    char e[16];
    snprintf(e, sizeof(e), "e%c%02d", power < 0 ? '-' : '+', abs(power));
    put(b, e);
  } else if (power < 0) {
    put(b, "0.");
    for (int i = -1; i > power; i--)
      put(b, "0");
    append(b, digits, (size_t)count);
  } else {
    for (int i = 0; i <= power; i++)
      append(b, i < count ? digits + i : "0", 1);
    put(b, ".");
    if (count > power + 1)
      append(b, digits + power + 1, (size_t)(count - power - 1));
    else
      put(b, "0");
  }
}
static void encode(Buffer *b, yyjson_val *v) {
  if (yyjson_is_str(v))
    string(b, v);
  else if (yyjson_is_raw(v))
    numeric(b, v);
  else if (yyjson_is_null(v))
    put(b, "null");
  else if (yyjson_is_bool(v))
    put(b, yyjson_get_bool(v) ? "true" : "false");
  else if (yyjson_is_arr(v)) {
    put(b, "[");
    size_t i, n;
    yyjson_val *x;
    yyjson_arr_foreach(v, i, n, x) {
      if (i)
        put(b, ",");
      encode(b, x);
    }
    put(b, "]");
  } else if (yyjson_is_obj(v)) {
    put(b, "{");
    yyjson_val **sorted = keys(v);
    for (size_t i = 0; i < yyjson_obj_size(v); i++) {
      if (i)
        put(b, ",");
      string(b, sorted[i]);
      put(b, ":");
      encode(b, yyjson_obj_iter_get_val(sorted[i]));
    }
    put(b, "}");
  } else
    fail("malformed_json");
}
char *canonical(yyjson_val *v) {
  Buffer b = {mem(LIMIT + 1), 0};
  encode(&b, v);
  return b.s;
}
