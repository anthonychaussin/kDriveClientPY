from enum import Enum


class ConflictMode(str, Enum):
    ERROR = "error"
    RENAME = "rename"
    VERSION = "version"


class Order(str, Enum):
    ASC = "asc"
    DESC = "desc"


class OrderBy(str, Enum):
    ADDED_AT = "added_at"
    LAST_MODIFIED_AT = "last_modified_at"
    MIME_TYPE = "mime_type"
    NAME = "name"
    REVISED_AT = "revised_at"
    SIZE = "size"
    TYPE = "type"
    UPDATED_AT = "updated_at"
    RELEVANCE = "relevance"


class EntryType(str, Enum):
    DIR = "dir"
    FILE = "file"
    VAULT = "vault"


class SearchDepth(str, Enum):
    CHILD = "child"
    UNLIMITED = "unlimited"


class QueryScope(str, Enum):
    ALL = "all"
    CONTENT = "content"
    FILENAME = "filename"
