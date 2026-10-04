"""Restricted YAML and deterministic JSON. Never execute YAML constructors."""

import yaml

from .errors import PolicyError
from .json_codec import canonical as canonical
from .json_codec import digest as digest
from .json_codec import json_value as json_value


class RestrictedLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise PolicyError("invalid_yaml", "Mapping keys must be strings")
            if key in result:
                raise PolicyError("duplicate_key", "Duplicate mapping key")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def parse_yaml(text: str, location: str = "") -> dict:
    try:
        depth = 0
        for event in yaml.parse(text, Loader=RestrictedLoader):
            if isinstance(event, yaml.AliasEvent) or getattr(event, "anchor", None):
                raise PolicyError("invalid_yaml", "YAML anchors and aliases are unsupported")
            if getattr(event, "tag", None):
                raise PolicyError("invalid_yaml", "Explicit YAML tags are unsupported")
            if isinstance(event, (yaml.MappingStartEvent, yaml.SequenceStartEvent)):
                depth += 1
                if depth > 24:
                    raise PolicyError("depth_limit", "YAML exceeds depth 24")
            elif isinstance(event, (yaml.MappingEndEvent, yaml.SequenceEndEvent)):
                depth -= 1
        value = yaml.load(text, Loader=RestrictedLoader)
        json_value(value)
        if not isinstance(value, dict):
            raise PolicyError("invalid_yaml", "Expected a mapping")
        return value
    except PolicyError as exc:
        raise PolicyError(exc.code, exc.message, location) from None
    except (yaml.YAMLError, RecursionError, ValueError):
        # Parser exceptions can echo source content, which may contain private rules.
        raise PolicyError("invalid_yaml", "Invalid YAML document", location) from None
