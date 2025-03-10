import string
from typing import Any, Dict, List, Optional, Union

from ._exceptions import ParseError, ValidationError

## Grammar


HTAB = "\t"
SP = " "
obs_text = "".join(chr(i) for i in range(0x80, 0xFF + 1))  # 0x80-0xFF

tchar = "!#$%&'*+-.^_`|~0123456789" + string.ascii_letters
qdtext = "".join(
    [
        HTAB,
        SP,
        "\x21",
        "".join(chr(i) for i in range(0x23, 0x5B + 1)),  # 0x23-0x5b
        "".join(chr(i) for i in range(0x5D, 0x7E + 1)),  # 0x5D-0x7E
        obs_text,
    ]
)

TIME_FIELDS = [
    "max_age",
    "max_stale",
    "min_fresh",
    "s_maxage",
]

BOOLEAN_FIELDS = [
    "immutable",
    "must_revalidate",
    "must_understand",
    "no_store",
    "no_transform",
    "only_if_cached",
    "public",
    "proxy_revalidate",
]

LIST_FIELDS = ["no_cache", "private"]

__all__ = (
    "CacheControl",
    "Vary",
)


def strip_ows_around(text: str) -> str:
    return text.strip(" ").strip("\t")


def normalize_directive(text: str) -> str:
    return text.replace("-", "_")


def parse_cache_control(cache_control_values: List[str]) -> "CacheControl":
    directives = {}

    for cache_control_value in cache_control_values:
        if "no-cache=" in cache_control_value or "private=" in cache_control_value:
            cache_control_splited = [cache_control_value]
        else:
            cache_control_splited = cache_control_value.split(",")

        for directive in cache_control_splited:
            key: str = ""
            value: Optional[str] = None
            dquote = False

            if not directive:
                raise ParseError("The directive should not be left blank.")

            directive = strip_ows_around(directive)

            if not directive:
                raise ParseError("The directive should not contain only whitespaces.")

            for i, key_char in enumerate(directive):
                if key_char == "=":
                    value = directive[i + 1 :]

                    if not value:
                        raise ParseError("The directive value cannot be left blank.")

                    if value[0] == '"':
                        dquote = True
                    if dquote and value[-1] != '"':
                        raise ParseError("Invalid quotes around the value.")

                    if not dquote:
                        for value_char in value:
                            if value_char not in tchar:
                                raise ParseError(
                                    f"The character '{value_char!r}' " "is not permitted for the unquoted values."
                                )
                    else:
                        for value_char in value[1:-1]:
                            if value_char not in qdtext:
                                raise ParseError(
                                    f"The character '{value_char!r}' " "is not permitted for the quoted values."
                                )
                    break

                if key_char not in tchar:
                    raise ParseError(f"The character '{key_char!r}' is not permitted in the directive name.")
                key += key_char
            directives[key] = value
    validated_data = CacheControl.validate(directives)
    return CacheControl(**validated_data)


class Vary:
    def __init__(self, values: List[str]) -> None:
        self._values = values

    @classmethod
    def from_value(cls, vary_values: List[str]) -> "Vary":
        values = []

        for vary_value in vary_values:
            for field_name in vary_value.split(","):
                field_name = field_name.strip()
                values.append(field_name)
        return Vary(values)


class CacheControl:
    def __init__(
        self,
        immutable: bool = False,  # [RFC8246]
        max_age: Optional[int] = None,  # [RFC9111, Section 5.2.1.1, 5.2.2.1]
        max_stale: Optional[int] = None,  # [RFC9111, Section 5.2.1.2]
        min_fresh: Optional[int] = None,  # [RFC9111, Section 5.2.1.3]
        must_revalidate: bool = False,  # [RFC9111, Section 5.2.2.2]
        must_understand: bool = False,  # [RFC9111, Section 5.2.2.3]
        no_cache: Union[bool, List[str]] = False,  # [RFC9111, Section 5.2.1.4, 5.2.2.4]
        no_store: bool = False,  # [RFC9111, Section 5.2.1.5, 5.2.2.5]
        no_transform: bool = False,  # [RFC9111, Section 5.2.1.6, 5.2.2.6]
        only_if_cached: bool = False,  # [RFC9111, Section 5.2.1.7]
        private: Union[bool, List[str]] = False,  # [RFC9111, Section 5.2.2.7]
        proxy_revalidate: bool = False,  # [RFC9111, Section 5.2.2.8]
        public: bool = False,  # [RFC9111, Section 5.2.2.9]
        s_maxage: Optional[int] = None,  # [RFC9111, Section 5.2.2.10]
    ) -> None:
        self.immutable = immutable
        self.max_age = max_age
        self.max_stale = max_stale
        self.min_fresh = min_fresh
        self.must_revalidate = must_revalidate
        self.must_understand = must_understand
        self.no_cache = no_cache
        self.no_store = no_store
        self.no_transform = no_transform
        self.only_if_cached = only_if_cached
        self.private = private
        self.proxy_revalidate = proxy_revalidate
        self.public = public
        self.s_maxage = s_maxage

    @classmethod
    def validate(cls, directives: Dict[str, Any]) -> Dict[str, Any]:
        validated_data: Dict[str, Any] = {}

        for key, value in directives.items():
            key = normalize_directive(key)
            if key in TIME_FIELDS:
                if value is None:
                    raise ValidationError(f"The directive '{key}' necessitates a value.")

                if value[0] == '"' or value[-1] == '"':
                    raise ValidationError(f"The argument '{key}' should be an integer, but a quote was found.")

                try:
                    validated_data[key] = int(value)
                except Exception:
                    raise ValidationError(f"The argument '{key}' should be an integer, but got '{value!r}'.")
            elif key in BOOLEAN_FIELDS:
                if value is not None:
                    raise ValidationError(f"The directive '{key}' should have no value, but it does.")
                validated_data[key] = True
            elif key in LIST_FIELDS:
                if value is None:
                    validated_data[key] = True
                else:
                    values = []
                    for list_value in value[1:-1].split(","):
                        if not list_value:
                            raise ValidationError("The list value must not be empty.")
                        list_value = strip_ows_around(list_value)
                        values.append(list_value)
                    validated_data[key] = values

        return validated_data

    def __repr__(self) -> str:
        fields = ""

        for key in TIME_FIELDS:
            key = key.replace("-", "_")
            value = getattr(self, key)
            if value:
                fields += f"{key}={value}, "

        for key in BOOLEAN_FIELDS:
            key = key.replace("-", "_")
            value = getattr(self, key)
            if value:
                fields += f"{key}, "

        fields = fields[:-2]

        return f"<{type(self).__name__} {fields}>"
