/* HumanWill remote hook client. No local policy/model implementation. */
#include "native.h"
#include "platform.h"
#include "schemas.h"
#include <ctype.h>
#include <curl/curl.h>
#include <setjmp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifndef HUMANWILL_NATIVE_VERSION
#define HUMANWILL_NATIVE_VERSION "0.1.0.dev2-native"
#endif
static const char *ca_file;

static jmp_buf failure;
static const char *error_code;
static CURL *curl;
static CURLU *url;
static struct curl_slist *headers;
static char *url_parts[8];
void fail(const char *code) {
  error_code = code;
  longjmp(failure, 1);
}
static char *format(const char *a, const char *b, const char *c,
                    const char *d) {
  size_t n = strlen(a) + strlen(b) + strlen(c) + strlen(d);
  if (n > LIMIT)
    fail("payload_limit");
  char *s = mem(n + 1);
  snprintf(s, n + 1, "%s%s%s%s", a, b, c, d);
  return s;
}
static void sha256(const char *s, char out[65]) {
  unsigned char digest[32];
  if (!hw_sha256(s, strlen(s), digest))
    fail("crypto_error");
  for (size_t i = 0; i < 32; i++)
    snprintf(out + 2 * i, 3, "%02x", digest[i]);
}
static char *read_input(void) {
  char *s = mem(LIMIT + 2);
  size_t n = fread(s, 1, LIMIT + 1, stdin);
  if (n > LIMIT)
    fail("payload_limit");
  if (ferror(stdin))
    fail("malformed_json");
  /* Return size separately through caller strlen is unsafe for raw embedded
   * NUL. */
  if (memchr(s, 0, n))
    fail("malformed_json");
  s[n] = 0;
  return s;
}
static void check_url(const char *origin) {
  if (strlen(origin) > 4096)
    fail("invalid_service_url");
  for (const unsigned char *p = (const unsigned char *)origin; *p; p++)
    if (*p <= 32 || *p == 127)
      fail("invalid_service_url");
  url = curl_url();
  if (!url)
    fail("memory_error");
  if (curl_url_set(url, CURLUPART_URL, origin, 0))
    fail("invalid_service_url");
  CURLUPart parts[] = {CURLUPART_SCHEME,   CURLUPART_HOST,   CURLUPART_USER,
                       CURLUPART_PASSWORD, CURLUPART_QUERY,  CURLUPART_FRAGMENT,
                       CURLUPART_PATH,     CURLUPART_OPTIONS};
  for (size_t i = 0; i < 8; i++)
    curl_url_get(url, parts[i], &url_parts[i], 0);
  const char *scheme = url_parts[0], *host = url_parts[1], *path = url_parts[6];
  if (!scheme || !host || (strcmp(scheme, "https") && strcmp(scheme, "http")) ||
      url_parts[2] || url_parts[3] || url_parts[4] || url_parts[5] ||
      url_parts[7] || (path && strcmp(path, "/")))
    fail("invalid_service_url");
  if (!strcmp(scheme, "http") && strcmp(host, "localhost") &&
      strcmp(host, "127.0.0.1") && strcmp(host, "[::1]"))
    fail("insecure_service_url");
}
typedef struct {
  char data[LIMIT + 1];
  size_t size;
  bool bad_encoding;
  size_t header_bytes;
} Reply;
static size_t body_cb(char *ptr, size_t size, size_t count, void *arg) {
  Reply *r = arg;
  if (size && count > LIMIT / size)
    return 0;
  size_t n = size * count;
  if (n > LIMIT - r->size)
    return 0;
  memcpy(r->data + r->size, ptr, n);
  r->size += n;
  r->data[r->size] = 0;
  return n;
}
static size_t header_cb(char *ptr, size_t size, size_t count, void *arg) {
  Reply *r = arg;
  if (size && count > LIMIT / size)
    return 0;
  size_t n = size * count;
  if (n > LIMIT - r->header_bytes)
    return 0;
  r->header_bytes += n;
  if (n >= 17 && !hw_ascii_ncasecmp(ptr, "Content-Encoding:", 17)) {
    size_t start = 17, end = n;
    while (start < end && (ptr[start] == ' ' || ptr[start] == '\t'))
      start++;
    while (end > start && isspace((unsigned char)ptr[end - 1]))
      end--;
    if (end - start != 8 || memcmp(ptr + start, "identity", 8))
      r->bad_encoding = true;
  }
  return n;
}
#define SET(option, value)                                                     \
  do {                                                                         \
    if (curl_easy_setopt(curl, option, value) != CURLE_OK)                     \
      fail("transport_configuration");                                         \
  } while (0)
static yyjson_val *request(const char *origin, const char *runtime,
                           const char *event, const char *token, long timeout,
                           const char *payload) {
  check_url(origin);
  if (!token || strlen(token) < 32 || strlen(token) > 8192)
    fail("missing_credentials");
  for (const unsigned char *p = (const unsigned char *)token; *p; p++)
    if (*p <= 32 || *p >= 127)
      fail("missing_credentials");
  char *path = format("/v1/hooks/", runtime, "/", event);
  if (curl_url_set(url, CURLUPART_PATH, path, 0))
    fail("invalid_service_url");
  curl = curl_easy_init();
  if (!curl)
    fail("memory_error");
  const char *auth = format("Authorization: Bearer ", token, "", "");
  headers = curl_slist_append(headers, auth);
  if (!headers)
    fail("memory_error");
  struct curl_slist *next =
      curl_slist_append(headers, "Content-Type: application/json");
  if (!next)
    fail("memory_error");
  headers = next;
  next = curl_slist_append(headers, "Accept-Encoding: identity");
  if (!next)
    fail("memory_error");
  headers = next;
  Reply *reply = mem(sizeof(*reply));
  SET(CURLOPT_CURLU, url);
  SET(CURLOPT_HTTPHEADER, headers);
  SET(CURLOPT_POSTFIELDS, payload);
  SET(CURLOPT_POSTFIELDSIZE, (long)strlen(payload));
  SET(CURLOPT_PROXY, "");
  SET(CURLOPT_FOLLOWLOCATION, 0L);
  SET(CURLOPT_MAXREDIRS, 0L);
  SET(CURLOPT_NETRC, (long)CURL_NETRC_IGNORED);
  SET(CURLOPT_UNRESTRICTED_AUTH, 0L);
  SET(CURLOPT_SSL_VERIFYPEER, 1L);
  SET(CURLOPT_SSL_VERIFYHOST, 2L);
  SET(CURLOPT_PROTOCOLS_STR, "http,https");
  if (ca_file)
    SET(CURLOPT_CAINFO, ca_file);
#if defined(__APPLE__)
  else
    SET(CURLOPT_SSL_OPTIONS, (long)CURLSSLOPT_NATIVE_CA);
#endif
  SET(CURLOPT_TIMEOUT_MS, timeout);
  SET(CURLOPT_CONNECTTIMEOUT_MS, timeout);
  SET(CURLOPT_NOSIGNAL, 1L);
  SET(CURLOPT_WRITEFUNCTION, body_cb);
  SET(CURLOPT_WRITEDATA, reply);
  SET(CURLOPT_HEADERFUNCTION, header_cb);
  SET(CURLOPT_HEADERDATA, reply);
  CURLcode code = curl_easy_perform(curl);
  long status = 0;
  curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &status);
  if (code != CURLE_OK || status != 200 || reply->bad_encoding)
    fail("service_response");
  return parse(reply->data, reply->size);
}
static yyjson_val *normalize(yyjson_val *payload, bool local, bool prompt,
                             const char *event, const char **wire) {
  if (!yyjson_is_obj(payload))
    fail("unsupported_payload");
  if (local && !isstr(get(payload, "hook_event_name"), event))
    fail("unsupported_payload");
  char *content;
  if (prompt) {
    yyjson_val *p = get(payload, "prompt");
    if (!yyjson_is_str(p))
      fail("unsupported_payload");
    char *text = canonical(p);
    content = format(
        "{\"id\":\"part-0\",\"kind\":\"text\",\"role\":\"user\",\"text\":",
        text, "}", "");
    *wire =
        format(local ? "{\"hook_event_name\":\"UserPromptSubmit\",\"prompt\":"
                     : "{\"prompt\":",
               text, "}", "");
  } else {
    yyjson_val *name = get(payload, local ? "tool_name" : "toolName");
    yyjson_val *arg = get(payload, local ? "tool_input" : "toolArgs"),
               *original = arg;
    if (!local && yyjson_is_str(arg))
      arg = parse(yyjson_get_str(arg), yyjson_get_len(arg));
    if (!yyjson_is_str(name) || !yyjson_is_obj(arg))
      fail("unsupported_payload");
    char *n = canonical(name), *a = canonical(arg);
    content = format("{\"id\":\"part-0\",\"kind\":\"tool_action\",\"name\":", n,
                     ",\"arguments\":", a);
    content = format(content, "}", "", "");
    *wire = format(
        local ? "{\"hook_event_name\":\"PreToolUse\",\"tool_name\":"
              : "{\"toolName\":",
        n, local ? ",\"tool_input\":" : ",\"toolArgs\":", canonical(original));
    *wire = format(*wire, "}", "", "");
  }
  char *normalized =
      format("{\"format\":\"humanwill.request/"
             "1\",\"request_id\":\"event-00000000000000000000000000000000\","
             "\"stage\":\"",
             prompt ? "prompt" : "tool_action", "\",\"content\":[", content);
  normalized = format(normalized,
                      "],\"coverage\":{\"complete\":true,\"inspected\":[\"part-"
                      "0\"],\"omitted\":[]}}",
                      "", "");
  yyjson_val *v = parse(normalized, strlen(normalized));
  if (!validate(parse(schema_request, strlen(schema_request)), v))
    fail("schema_error");
  canonical(v); /* Same canonical byte limit as Python. */
  return v;
}
static void validate_result(yyjson_val *r, yyjson_val *normalized) {
  const char *schema =
      isstr(get(r, "format"), "humanwill.result/2")   ? schema_result_v2
      : isstr(get(r, "format"), "humanwill.result/3") ? schema_result_v3
      : isstr(get(r, "format"), "humanwill.result/4") ? schema_result_v4
                                                      : NULL;
  if (!schema || !validate(parse(schema, strlen(schema)), r))
    fail("schema_error");
  canonical(r);
  yyjson_val *policies = get(r, "policies");
  size_t i, n;
  yyjson_val *p;
  yyjson_arr_foreach(
      policies, i, n,
      p) for (size_t j = 0; j < i;
              j++) if (equal(get(p, "policy_id"),
                             get(yyjson_arr_get(policies, j), "policy_id")))
      fail("duplicate_policy_id");
  if (!equal(get(r, "coverage"), get(normalized, "coverage")))
    fail("event_mismatch");
  /* Rebuild with the service-generated request ID before hashing, as Python
   * does. */
  char *c = canonical(get(normalized, "content")),
       *id = canonical(get(r, "request_id"));
  char *s = format(
      "{\"content\":", c,
      ",\"coverage\":{\"complete\":true,\"inspected\":[\"part-0\"],\"omitted\":"
      "[]},\"format\":\"humanwill.request/1\",\"request_id\":",
      id);
  s = format(s, ",\"stage\":", canonical(get(normalized, "stage")), "}");
  char hash[65];
  sha256(s, hash);
  if (!isstr(get(r, "request_sha256"), hash))
    fail("event_mismatch");
  if (yyjson_get_bool(get(r, "simulated")) &&
      !isstr(get(get(r, "enforcement"), "requested"), "none"))
    fail("service_response");
}
static void output(bool local, bool prompt, bool block) {
  const char *reason = "HumanWill policy check denied this operation";
  if (!block || (!local && prompt))
    puts("{}");
  else if (local && prompt)
    printf("{\"continue\":false,\"stopReason\":\"%s\"}\n", reason);
  else if (local)
    printf("{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\","
           "\"permissionDecision\":\"deny\",\"permissionDecisionReason\":\"%"
           "s\"}}\n",
           reason);
  else
    printf("{\"permissionDecision\":\"deny\",\"permissionDecisionReason\":\"%"
           "s\"}\n",
           reason);
}
int main(int argc, char **argv) {
  if (!hw_stdio_binary()) {
    fputs("Cannot initialize binary streams\n", stderr);
    return 2;
  }
  const char *runtime = NULL, *event = NULL, *origin = "http://127.0.0.1:8088",
             *env = "HUMANWILL_HOOK_TOKEN", *fallback = "block";
  long timeout = 6000;
  for (int i = 1; i < argc; i++) {
    const char *a = argv[i];
    if (!strcmp(a, "--version")) {
      puts(HUMANWILL_NATIVE_VERSION);
      return 0;
    }
    if (!strcmp(a, "--help")) {
      puts("humanwill-hook-c --runtime copilot_local|copilot_cli --event EVENT "
           "[--url ORIGIN] [--token-env NAME] [--timeout-ms 100..60000] "
           "[--on-error block|allow_monitor] [--ca-file PEM]");
      return 0;
    }
    if (i + 1 == argc) {
      fputs("Missing option value\n", stderr);
      return 2;
    }
    const char *v = argv[++i];
    if (!strcmp(a, "--runtime"))
      runtime = v;
    else if (!strcmp(a, "--event"))
      event = v;
    else if (!strcmp(a, "--url"))
      origin = v;
    else if (!strcmp(a, "--token-env"))
      env = v;
    else if (!strcmp(a, "--ca-file"))
      ca_file = v;
    else if (!strcmp(a, "--on-error"))
      fallback = v;
    else if (!strcmp(a, "--timeout-ms")) {
      char *end;
      timeout = strtol(v, &end, 10);
      if (!*v || *end || timeout < 100 || timeout > 60000)
        return 2;
    } else {
      fputs("Unknown option\n", stderr);
      return 2;
    }
  }
  if (!runtime || !event ||
      (strcmp(runtime, "copilot_local") && strcmp(runtime, "copilot_cli")) ||
      (strcmp(fallback, "block") && strcmp(fallback, "allow_monitor"))) {
    fputs("Invalid hook configuration\n", stderr);
    return 2;
  }
  bool local = !strcmp(runtime, "copilot_local");
  bool prompt =
      !strcmp(event, local ? "UserPromptSubmit" : "userPromptSubmitted");
  if (!prompt && strcmp(event, local ? "PreToolUse" : "preToolUse")) {
    output(local, false, true);
    return 2;
  }
  /* Volatile because failure jumps across the networking/validation code. */
  volatile bool blocked = !strcmp(fallback, "block");
  if (!setjmp(failure)) {
    if (curl_global_init(CURL_GLOBAL_DEFAULT))
      fail("transport_configuration");
    char *raw = read_input();
    const char *wire = NULL;
    yyjson_val *norm =
        normalize(parse(raw, strlen(raw)), local, prompt, event, &wire);
    yyjson_val *r = request(origin, runtime, event, getenv(env), timeout, wire);
    validate_result(r, norm);
    blocked = isstr(get(get(r, "enforcement"), "requested"), "block");
    fprintf(
        stderr,
        "{\"runtime\":\"%s\",\"event\":\"%s\",\"actual\":\"%s\",\"decision\":%"
        "s,\"requested\":%s,\"simulated\":%s,\"request_id\":%s,\"assessment_"
        "only\":%s}\n",
        runtime, event, !local && prompt ? "not_requested" : "unconfirmed",
        canonical(get(r, "decision")),
        !local && prompt ? "\"none\""
                         : canonical(get(get(r, "enforcement"), "requested")),
        yyjson_get_bool(get(r, "simulated")) ? "true" : "false",
        canonical(get(r, "request_id")), !local && prompt ? "true" : "false");
  } else {
    blocked = !strcmp(fallback, "block");
    fprintf(stderr,
            "{\"runtime\":\"%s\",\"event\":\"%s\",\"error\":\"%s\","
            "\"requested\":\"%s\",\"actual\":\"%s\",\"assessment_only\":%s}\n",
            runtime, event, error_code,
            blocked && (local || !prompt) ? "block" : "none",
            !local && prompt ? "not_requested" : "unconfirmed",
            !local && prompt ? "true" : "false");
  }
  output(local, prompt, blocked);
  if (curl)
    curl_easy_cleanup(curl);
  if (headers)
    curl_slist_free_all(headers);
  if (url)
    curl_url_cleanup(url);
  for (size_t i = 0; i < 8; i++)
    curl_free(url_parts[i]);
  curl_global_cleanup();
  json_cleanup();
  return 0;
}
