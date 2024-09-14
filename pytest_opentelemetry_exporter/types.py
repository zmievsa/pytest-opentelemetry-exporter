from typing import List, Literal, TypedDict

from typing_extensions import NotRequired

# Constants for Span flags
SPAN_FLAGS_DO_NOT_USE = 0
SPAN_FLAGS_TRACE_FLAGS_MASK = 0x000000FF
SPAN_FLAGS_CONTEXT_HAS_IS_REMOTE_MASK = 0x00000100
SPAN_FLAGS_CONTEXT_IS_REMOTE_MASK = 0x00000200

StatusCode = Literal["STATUS_CODE_UNSET", "STATUS_CODE_OK", "STATUS_CODE_ERROR"]

SpanKind = Literal[
    "SPAN_KIND_UNSPECIFIED",
    "SPAN_KIND_INTERNAL",
    "SPAN_KIND_SERVER",
    "SPAN_KIND_CLIENT",
    "SPAN_KIND_PRODUCER",
    "SPAN_KIND_CONSUMER",
]


class AnyValue(TypedDict, total=False):
    """The value is one of the listed fields. It is valid for all values to be unspecified
    in which case this AnyValue is considered to be "empty"."""

    stringValue: NotRequired[str]
    boolValue: NotRequired[bool]
    intValue: NotRequired[int]
    doubleValue: NotRequired[float]
    arrayValue: NotRequired["ArrayValue"]
    kvlistValue: NotRequired["KeyValueList"]
    bytesValue: NotRequired[str]


class ArrayValue(TypedDict):
    """ArrayValue is a list of AnyValue messages. We need ArrayValue as a message
    since oneof in AnyValue does not allow repeated fields."""

    values: List[AnyValue]


class KeyValue(TypedDict):
    """KeyValue is a key-value pair that is used to store Span attributes, Link
    attributes, etc."""

    key: str
    value: AnyValue


class KeyValueList(TypedDict):
    """KeyValueList is a list of KeyValue messages. We need KeyValueList as a message
    since `oneof` in AnyValue does not allow repeated fields. Everywhere else where we need
    a list of KeyValue messages (e.g. in Span) we use `repeated KeyValue` directly to
    avoid unnecessary extra wrapping (which slows down the protocol). The 2 approaches
    are semantically equivalent."""

    values: List[KeyValue]


class Resource(TypedDict):
    """Resource information.

    Set of attributes that describe the resource.
    Attribute keys MUST be unique (it is not allowed to have more than one
    attribute with the same key)."""

    attributes: List[KeyValue]
    droppedAttributesCount: NotRequired[int]


class InstrumentationScope(TypedDict, total=False):
    """InstrumentationScope information."""

    name: NotRequired[str]
    version: NotRequired[str]
    attributes: NotRequired[List[KeyValue]]
    droppedAttributesCount: NotRequired[int]


class Status(TypedDict, total=False):
    """The Status type defines a logical error model that is suitable for different
    programming environments, including REST APIs and RPC APIs."""

    message: NotRequired[str]
    code: NotRequired[StatusCode]


class Event(TypedDict):
    """Event is a time-stamped annotation of the span, consisting of user-supplied
    text description and key-value pairs."""

    timeUnixNano: int
    name: str
    attributes: NotRequired[List[KeyValue]]
    droppedAttributesCount: NotRequired[int]


class Link(TypedDict):
    """A pointer from the current span to another span in the same trace or in a
    different trace. For example, this can be used in batching operations,
    where a single batch handler processes multiple requests from different
    traces or when the handler receives a request from a different project."""

    traceId: str
    spanId: str
    traceState: NotRequired[str]
    attributes: NotRequired[List[KeyValue]]
    droppedAttributesCount: NotRequired[int]
    flags: NotRequired[int]


class Span(TypedDict):
    """A Span represents a single operation performed by a single component of the system.

    The next available field id is 17."""

    traceId: str
    spanId: str
    traceState: NotRequired[str]
    parentSpanId: NotRequired[str]
    flags: NotRequired[int]
    name: str
    kind: NotRequired[SpanKind]
    startTimeUnixNano: int
    endTimeUnixNano: int
    attributes: NotRequired[List[KeyValue]]
    droppedAttributesCount: NotRequired[int]
    links: NotRequired[List[Link]]
    droppedLinksCount: NotRequired[int]
    status: NotRequired[Status]
    events: NotRequired[List[Event]]
    droppedEventsCount: NotRequired[int]


class ScopeSpans(TypedDict):
    """A collection of Spans produced by an InstrumentationScope."""

    scope: NotRequired[InstrumentationScope]
    spans: List[Span]
    schemaUrl: NotRequired[str]


class ResourceSpans(TypedDict):
    """A collection of ScopeSpans from a Resource."""

    resource: NotRequired[Resource]
    scopeSpans: List[ScopeSpans]
    schemaUrl: NotRequired[str]


class TracesData(TypedDict):
    """TracesData represents the traces data that can be stored in a persistent storage,
    OR can be embedded by other protocols that transfer OTLP traces data but do
    not implement the OTLP protocol.

    The main difference between this message and collector protocol is that
    in this message there will not be any "control" or "metadata" specific to
    OTLP protocol.

    When new fields are added into this message, the OTLP request MUST be updated
    as well."""

    resourceSpans: List[ResourceSpans]


class BatchesData(TypedDict):
    batches: List[ResourceSpans]
