/* OS integration only; policy protocol and validation are shared on all
 * targets. */
#include "platform.h"
#include <stdio.h>
#if defined(_WIN32)
#include <bcrypt.h>
#include <fcntl.h>
#include <io.h>
#include <windows.h>
#elif defined(__APPLE__)
#include <CommonCrypto/CommonDigest.h>
#else
#include <openssl/sha.h>
#endif

int hw_stdio_binary(void) {
#ifdef _WIN32
  return _setmode(_fileno(stdin), _O_BINARY) != -1 &&
         _setmode(_fileno(stdout), _O_BINARY) != -1 &&
         _setmode(_fileno(stderr), _O_BINARY) != -1;
#else
  return 1;
#endif
}
int hw_sha256(const char *input, size_t length, unsigned char digest[32]) {
#ifdef _WIN32
  BCRYPT_ALG_HANDLE algorithm = NULL;
  if (length > 0xffffffffu ||
      BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, NULL,
                                  0) < 0)
    return 0;
  NTSTATUS status =
      BCryptHash(algorithm, NULL, 0, (PUCHAR)input, (ULONG)length, digest, 32);
  BCryptCloseAlgorithmProvider(algorithm, 0);
  return status >= 0;
#elif defined(__APPLE__)
  return CC_SHA256(input, (CC_LONG)length, digest) != NULL;
#else
  return SHA256((const unsigned char *)input, length, digest) != NULL;
#endif
}
int hw_ascii_ncasecmp(const char *a, const char *b, size_t length) {
  for (size_t i = 0; i < length; i++) {
    unsigned char x = (unsigned char)a[i], y = (unsigned char)b[i];
    if (x >= 'A' && x <= 'Z')
      x += 'a' - 'A';
    if (y >= 'A' && y <= 'Z')
      y += 'a' - 'A';
    if (x != y)
      return (int)x - (int)y;
  }
  return 0;
}
