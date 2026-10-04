CC = cc
PYTHON ?= python3
OUT ?= ../../artifacts/native-hook
CFLAGS ?= -O2 -std=c11 -Wall -Wextra -Werror -Wno-deprecated-declarations
UNAME := $(shell uname -s)
ifeq ($(UNAME),Darwin)
LDLIBS = -lcurl
else
LDLIBS = -lcurl -lcrypto -lm
endif

.PHONY: all probe
all: $(OUT)/humanwill-hook-c
probe: $(OUT)/canonical-probe

$(OUT):
	mkdir -p $(OUT)

$(OUT)/schemas.h: ../../src/humanwill_policies/schemas/request.json ../../src/humanwill_policies/schemas/result-v2.json ../../src/humanwill_policies/schemas/result-v3.json ../../src/humanwill_policies/schemas/result-v4.json generate_schemas.py | $(OUT)
	$(PYTHON) generate_schemas.py $@

$(OUT)/humanwill-hook-c: main.c platform.c json.c schema.c native.h vendor/yyjson/yyjson.c vendor/yyjson/yyjson.h $(OUT)/schemas.h
	$(CC) $(CFLAGS) -I$(OUT) -Ivendor/yyjson main.c platform.c json.c schema.c vendor/yyjson/yyjson.c $(LDLIBS) -o $@

$(OUT)/canonical-probe: canonical_probe.c platform.c json.c native.h vendor/yyjson/yyjson.c vendor/yyjson/yyjson.h | $(OUT)
	$(CC) $(CFLAGS) -Ivendor/yyjson canonical_probe.c platform.c json.c vendor/yyjson/yyjson.c $(LDLIBS) -o $@
