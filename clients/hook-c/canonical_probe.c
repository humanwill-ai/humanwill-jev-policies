/* Test-only executable: not part of the installed hook interface. */
#include "native.h"
#include "platform.h"
#include <stdio.h>
#include <stdlib.h>
void fail(const char *code) {
  fprintf(stderr, "%s\n", code);
  json_cleanup();
  exit(1);
}
int main(void) {
  if (!hw_stdio_binary())
    return 2;
  char *s = mem(LIMIT + 1);
  size_t n = fread(s, 1, LIMIT, stdin);
  puts(canonical(parse(s, n)));
  json_cleanup();
  return 0;
}
