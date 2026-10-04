#include "native.h"
#include <math.h>
#include <string.h>

static bool alpha(unsigned char c) {
  return (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z');
}
static bool digit(unsigned char c) { return c >= '0' && c <= '9'; }
static bool pattern(const char *rule, const char *s, size_t len) {
  /* Exactly the patterns allowlisted by generate_schemas.py; no OS regex
   * engine. */
  if (!strcmp(rule, "^[A-Za-z][A-Za-z0-9._-]{0,127}$")) {
    if (!len || len > 128 || !alpha((unsigned char)s[0]))
      return false;
    for (size_t i = 1; i < len; i++)
      if (!alpha((unsigned char)s[i]) && !digit((unsigned char)s[i]) &&
          s[i] != '.' && s[i] != '_' && s[i] != '-')
        return false;
    return true;
  }
  if (!strcmp(rule, "^[a-f0-9]{64}$")) {
    if (len != 64)
      return false;
    for (size_t i = 0; i < len; i++)
      if (!digit((unsigned char)s[i]) && !(s[i] >= 'a' && s[i] <= 'f'))
        return false;
    return true;
  }
  if (!strcmp(rule, "^(identity|documents|destination|environment|"
                    "authorization)\\.[a-z][a-z0-9_]{0,63}$")) {
    const char *prefixes[] = {"identity.", "documents.", "destination.",
                              "environment.", "authorization."};
    for (size_t j = 0; j < sizeof(prefixes) / sizeof(prefixes[0]); j++) {
      size_t prefix = strlen(prefixes[j]);
      if (len <= prefix || memcmp(s, prefixes[j], prefix))
        continue;
      if (len - prefix > 64 || s[prefix] < 'a' || s[prefix] > 'z')
        return false;
      for (size_t i = prefix + 1; i < len; i++)
        if (!(s[i] >= 'a' && s[i] <= 'z') && !digit((unsigned char)s[i]) &&
            s[i] != '_')
          return false;
      return true;
    }
  }
  return false;
}

static bool type(yyjson_val *v, yyjson_val *t) {
  if (isstr(t, "object"))
    return yyjson_is_obj(v);
  if (isstr(t, "array"))
    return yyjson_is_arr(v);
  if (isstr(t, "string"))
    return yyjson_is_str(v);
  if (isstr(t, "boolean"))
    return yyjson_is_bool(v);
  if (isstr(t, "null"))
    return yyjson_is_null(v);
  if (isstr(t, "number"))
    return yyjson_is_raw(v);
  if (isstr(t, "integer")) {
    if (!yyjson_is_raw(v))
      return false;
    if (!strpbrk(yyjson_get_raw(v), ".eE"))
      return true;
    double d = number(v);
    return isfinite(d) && floor(d) == d;
  }
  if (yyjson_is_arr(t)) {
    size_t i, n;
    yyjson_val *x;
    yyjson_arr_foreach(t, i, n, x) if (type(v, x)) return true;
  }
  return false;
}
static bool bounds(yyjson_val *s, const char *lo, const char *hi, double n) {
  yyjson_val *a = get(s, lo), *b = get(s, hi);
  return (!a || n >= number(a)) && (!b || n <= number(b));
}
bool validate(yyjson_val *s, yyjson_val *v) {
  if (!s || !v)
    return false;
  if (yyjson_is_bool(s))
    return yyjson_get_bool(s);
  yyjson_val *rule = get(s, "type");
  if (rule && !type(v, rule))
    return false;
  rule = get(s, "const");
  if (rule && !equal(rule, v))
    return false;
  rule = get(s, "enum");
  size_t i, n;
  yyjson_val *x, *key;
  if (rule) {
    bool found = false;
    yyjson_arr_foreach(rule, i, n, x) if (equal(x, v)) found = true;
    if (!found)
      return false;
  }
  rule = get(s, "oneOf");
  if (rule) {
    int matches = 0;
    yyjson_arr_foreach(rule, i, n, x) if (validate(x, v)) matches++;
    if (matches != 1)
      return false;
  }
  if (yyjson_is_raw(v) && !bounds(s, "minimum", "maximum", number(v)))
    return false;
  if (yyjson_is_str(v)) {
    const char *str = yyjson_get_str(v);
    size_t len = yyjson_get_len(v);
    if (!bounds(s, "minLength", "maxLength", (double)codepoints(str, len)))
      return false;
    rule = get(s, "pattern");
    if (rule) {
      if (isstr(rule, "\\S")) {
        if (!nonspace(str, len))
          return false;
      } else {
        if (!pattern(yyjson_get_str(rule), str, len))
          return false;
      }
    }
  }
  if (yyjson_is_arr(v)) {
    if (!bounds(s, "minItems", "maxItems", (double)yyjson_arr_size(v)))
      return false;
    rule = get(s, "items");
    yyjson_arr_foreach(v, i, n, x) {
      if (rule && !validate(rule, x))
        return false;
      if (yyjson_get_bool(get(s, "uniqueItems")))
        for (size_t j = 0; j < i; j++)
          if (equal(x, yyjson_arr_get(v, j)))
            return false;
    }
  }
  if (yyjson_is_obj(v)) {
    if (!bounds(s, "minProperties", "maxProperties",
                (double)yyjson_obj_size(v)))
      return false;
    rule = get(s, "required");
    yyjson_arr_foreach(rule, i, n,
                       x) if (!yyjson_obj_getn(v, yyjson_get_str(x),
                                               yyjson_get_len(x))) return false;
    yyjson_val *props = get(s, "properties"),
               *extra = get(s, "additionalProperties");
    yyjson_obj_foreach(v, i, n, key, x) {
      rule = yyjson_obj_getn(props, yyjson_get_str(key), yyjson_get_len(key));
      if (rule) {
        if (!validate(rule, x))
          return false;
      } else if (extra && !validate(extra, x))
        return false;
    }
  }
  return true;
}
