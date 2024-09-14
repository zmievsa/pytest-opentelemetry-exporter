from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, root_validator

# Constants for Span flags
SPAN_FLAGS_DO_NOT_USE = 0
SPAN_FLAGS_TRACE_FLAGS_MASK = 0x000000FF
SPAN_FLAGS_CONTEXT_HAS_IS_REMOTE_MASK = 0x00000100
SPAN_FLAGS_CONTEXT_IS_REMOTE_MASK = 0x00000200


class StrEnum(str, Enum):
    pass


class AnyValue(BaseModel):
    """The value is one of the listed fields. It is valid for all values to be unspecified
    in which case this AnyValue is considered to be "empty"."""

    stringValue: Optional[str] = None
    boolValue: Optional[bool] = None
    intValue: Optional[int] = None
    doubleValue: Optional[float] = None
    arrayValue: Optional["ArrayValue"] = None
    kvlistValue: Optional["KeyValueList"] = None
    bytesValue: Optional[bytes] = None

    @root_validator(pre=True)
    def check_oneof(cls, values: dict[str, Any]):
        fields = [
            "stringValue",
            "boolValue",
            "intValue",
            "doubleValue",
            "arrayValue",
            "kvlistValue",
            "bytesValue",
        ]
        set_fields = [field for field in fields if values.get(field) is not None]
        if len(set_fields) > 1:
            raise ValueError("Only one of the fields in AnyValue can be set")
        return values


class ArrayValue(BaseModel):
    """ArrayValue is a list of AnyValue messages. We need ArrayValue as a message
    since oneof in AnyValue does not allow repeated fields."""

    values: list[AnyValue] = Field(..., description="Array of values. The array may be empty (contain 0 elements).")


class KeyValue(BaseModel):
    """KeyValue is a key-value pair that is used to store Span attributes, Link
    attributes, etc."""

    key: str
    value: AnyValue


class KeyValueList(BaseModel):
    """KeyValueList is a list of KeyValue messages. We need KeyValueList as a message
    since `oneof` in AnyValue does not allow repeated fields. Everywhere else where we need
    a list of KeyValue messages (e.g. in Span) we use `repeated KeyValue` directly to
    avoid unnecessary extra wrapping (which slows down the protocol). The 2 approaches
    are semantically equivalent."""

    values: list[KeyValue] = Field(
        ...,
        description=(
            "A collection of key/value pairs of key-value pairs. The list may be empty "
            "(may contain 0 elements). The keys MUST be unique (it is not allowed to have "
            "more than one value with the same key)."
        ),
    )


class Resource(BaseModel):
    """Resource information.

    Set of attributes that describe the resource.
    Attribute keys MUST be unique (it is not allowed to have more than one
    attribute with the same key)."""

    attributes: list[KeyValue] = Field(
        ...,
        description=(
            "Set of attributes that describe the resource. Attribute keys MUST be unique "
            "(it is not allowed to have more than one attribute with the same key)."
        ),
    )
    droppedAttributesCount: Optional[int] = Field(
        None,
        description=(
            "dropped_attributes_count is the number of dropped attributes. If the value is 0, "
            "then no attributes were dropped."
        ),
    )


class InstrumentationScope(BaseModel):
    """InstrumentationScope information."""

    name: Optional[str] = None
    version: Optional[str] = None
    attributes: Optional[list[KeyValue]] = None
    droppedAttributesCount: Optional[int] = None


class StatusCode(StrEnum):
    """For the semantics of status codes see
    https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/trace/api.md#set-status"""

    STATUS_CODE_UNSET = "STATUS_CODE_UNSET"
    STATUS_CODE_OK = "STATUS_CODE_OK"
    STATUS_CODE_ERROR = "STATUS_CODE_ERROR"


class Status(BaseModel):
    """The Status type defines a logical error model that is suitable for different
    programming environments, including REST APIs and RPC APIs."""

    message: Optional[str] = Field(None, description="A developer-facing human readable error message.")
    code: Optional[StatusCode] = Field(default=None, description="The status code.")


class SpanKind(StrEnum):
    """Distinguishes between spans generated in a particular context. For example,
    two spans with the same name may be distinguished using `CLIENT` (caller)
    and `SERVER` (callee) to identify queueing latency associated with the span."""

    SPAN_KIND_UNSPECIFIED = "SPAN_KIND_UNSPECIFIED"
    SPAN_KIND_INTERNAL = "SPAN_KIND_INTERNAL"
    SPAN_KIND_SERVER = "SPAN_KIND_SERVER"
    SPAN_KIND_CLIENT = "SPAN_KIND_CLIENT"
    SPAN_KIND_PRODUCER = "SPAN_KIND_PRODUCER"
    SPAN_KIND_CONSUMER = "SPAN_KIND_CONSUMER"


class Event(BaseModel):
    """Event is a time-stamped annotation of the span, consisting of user-supplied
    text description and key-value pairs."""

    timeUnixNano: int = Field(..., description="time_unix_nano is the time the event occurred.")
    name: str = Field(
        ...,
        description=("name of the event.\n\nThis field is semantically required to be set to non-empty string."),
    )
    attributes: Optional[list[KeyValue]] = Field(
        None,
        description=(
            "attributes is a collection of attribute key/value pairs on the event. Attribute keys MUST be unique "
            "(it is not allowed to have more than one attribute with the same key)."
        ),
    )
    droppedAttributesCount: Optional[int] = Field(
        None,
        description=(
            "dropped_attributes_count is the number of dropped attributes. If the value is 0, then no attributes were dropped."
        ),
    )


class Link(BaseModel):
    """A pointer from the current span to another span in the same trace or in a
    different trace. For example, this can be used in batching operations,
    where a single batch handler processes multiple requests from different
    traces or when the handler receives a request from a different project."""

    traceId: bytes = Field(
        ...,
        description=("A unique identifier of a trace that this linked span is part of. The ID is a 16-byte array."),
    )
    spanId: bytes = Field(..., description="A unique identifier for the linked span. The ID is an 8-byte array.")
    traceState: Optional[str] = Field(None, description="The trace_state associated with the link.")
    attributes: Optional[list[KeyValue]] = Field(
        None,
        description=(
            "attributes is a collection of attribute key/value pairs on the link. Attribute keys MUST be unique "
            "(it is not allowed to have more than one attribute with the same key)."
        ),
    )
    droppedAttributesCount: Optional[int] = Field(
        None,
        description=(
            "dropped_attributes_count is the number of dropped attributes. If the value is 0, then no attributes were dropped."
        ),
    )
    flags: Optional[int] = Field(
        None,
        description=(
            "Flags, a bit field.\n\nBits 0-7 (8 least significant bits) are the trace flags as defined in W3C Trace Context "
            "specification. To read the 8-bit W3C trace flag, use `flags & SPAN_FLAGS_TRACE_FLAGS_MASK`.\n\nSee "
            "https://www.w3.org/TR/trace-context-2/#trace-flags for the flag definitions.\n\nBits 8 and 9 are used to indicate "
            "that the link is remote. Bit 8 (`HAS_IS_REMOTE`) indicates whether the value is known. Bit 9 (`IS_REMOTE`) indicates "
            "whether the span or link is remote.\n\nReaders MUST NOT assume that bits 10-31 (22 most significant bits) will be zero. "
            "When creating new spans, bits 10-31 (most-significant 22-bits) MUST be zero.\n\n[Optional]."
        ),
    )


class Span(BaseModel):
    """A Span represents a single operation performed by a single component of the system.

    The next available field id is 17."""

    traceId: bytes = Field(
        ...,
        description=(
            "A unique identifier for a trace. All spans from the same trace share the same "
            "`traceId`. The ID is a 16-byte array. An ID with all zeroes OR of length other "
            "than 16 bytes is considered invalid (empty string in OTLP/JSON is zero-length and "
            "thus is also invalid).\n\nThis field is required."
        ),
    )
    spanId: bytes = Field(
        ...,
        description=(
            "A unique identifier for a span within a trace, assigned when the span is created. "
            "The ID is an 8-byte array. An ID with all zeroes OR of length other than 8 bytes is "
            "considered invalid (empty string in OTLP/JSON is zero-length and thus is also invalid).\n\n"
            "This field is required."
        ),
    )
    traceState: Optional[str] = Field(
        None,
        description=(
            "trace_state conveys information about request position in multiple distributed "
            "tracing graphs. It is a trace_state in w3c-trace-context format: "
            "https://www.w3.org/TR/trace-context/#tracestate-header See also "
            "https://github.com/w3c/distributed-tracing for more details about this field."
        ),
    )
    parentSpanId: Optional[bytes] = Field(
        None,
        description=(
            "The `spanId` of this span's parent span. If this is a root span, then this field "
            "must be empty. The ID is an 8-byte array."
        ),
    )
    flags: Optional[int] = Field(
        None,
        description=(
            "Flags, a bit field.\n\nBits 0-7 (8 least significant bits) are the trace flags as "
            "defined in W3C Trace Context specification. To read the 8-bit W3C trace flag, use "
            "`flags & SPAN_FLAGS_TRACE_FLAGS_MASK`.\n\nSee https://www.w3.org/TR/trace-context-2/#trace-flags "
            "for the flag definitions.\n\nBits 8 and 9 represent the 3 states of whether a span's parent "
            "is remote. The states are (unknown, is not remote, is remote). To read whether the value is known, "
            "use `(flags & SPAN_FLAGS_CONTEXT_HAS_IS_REMOTE_MASK) != 0`. To read whether the span is remote, "
            "use `(flags & SPAN_FLAGS_CONTEXT_IS_REMOTE_MASK) != 0`.\n\nWhen creating span messages, if the "
            "message is logically forwarded from another source with an equivalent flags fields (i.e., usually "
            "another OTLP span message), the field SHOULD be copied as-is. If creating from a source that does "
            "not have an equivalent flags field (such as a runtime representation of an OpenTelemetry span), the "
            "high 22 bits MUST be set to zero.\n\nReaders MUST NOT assume that bits 10-31 (22 most significant bits) "
            "will be zero.\n\n[Optional]."
        ),
    )
    name: str = Field(
        ...,
        description=(
            "A description of the span's operation.\n\nFor example, the name can be a qualified method name or a file "
            "name and a line number where the operation is called. A best practice is to use the same display name "
            "at the same call point in an application. This makes it easier to correlate spans in different traces.\n\n"
            "This field is semantically required to be set to non-empty string. Empty value is equivalent to an unknown "
            "span name.\n\nThis field is required."
        ),
    )
    kind: Optional[SpanKind] = Field(
        None,
        description=(
            "Distinguishes between spans generated in a particular context. For example, two spans with the same name "
            "may be distinguished using `CLIENT` (caller) and `SERVER` (callee) to identify queueing latency associated "
            "with the span."
        ),
    )
    startTimeUnixNano: int = Field(
        ...,
        description=(
            "startTimeUnixNano is the start time of the span. On the client side, this is the time kept by the local "
            "machine where the span execution starts. On the server side, this is the time when the server's application "
            "handler starts running. Value is UNIX Epoch time in nanoseconds since 00:00:00 UTC on 1 January 1970.\n\n"
            "This field is semantically required and it is expected that end_time >= start_time."
        ),
    )
    endTimeUnixNano: int = Field(
        ...,
        description=(
            "endTimeUnixNano is the end time of the span. On the client side, this is the time kept by the local machine "
            "where the span execution ends. On the server side, this is the time when the server application handler stops "
            "running. Value is UNIX Epoch time in nanoseconds since 00:00:00 UTC on 1 January 1970.\n\n"
            "This field is semantically required and it is expected that end_time >= start_time."
        ),
    )
    attributes: Optional[list[KeyValue]] = Field(
        None,
        description=(
            "attributes is a collection of key/value pairs. Note, global attributes like server name can be set using the "
            "resource API. Examples of attributes:\n\n"
            '    "/http/user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/71.0.3578.98 Safari/537.36"\n'
            '    "/http/server_latency": 300\n'
            '    "example.com/myattribute": true\n'
            '    "example.com/score": 10.239\n\n'
            "The OpenTelemetry API specification further restricts the allowed value types: "
            "https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/common/README.md#attribute "
            "Attribute keys MUST be unique (it is not allowed to have more than one attribute with the same key)."
        ),
    )
    droppedAttributesCount: Optional[int] = Field(
        None,
        description=(
            "dropped_attributes_count is the number of attributes that were discarded. Attributes can be discarded because "
            "their keys are too long or because there are too many attributes. If this value is 0, then no attributes were dropped."
        ),
    )

    links: Optional[list["Link"]] = Field(
        None,
        description=(
            "links is a collection of Links, which are references from this span to a span in the same or different trace."
        ),
    )
    droppedLinksCount: Optional[int] = Field(
        None,
        description=(
            "dropped_links_count is the number of dropped links after the maximum size was enforced. If this value is 0, then no links were dropped."
        ),
    )
    status: Optional[Status] = Field(
        None,
        description=(
            "An optional final status for this span. Semantically when Status isn't set, it means span's status code is unset, "
            "i.e. assume STATUS_CODE_UNSET (code = 0)."
        ),
    )
    events: Optional[list[Event]] = Field(None, description="events is a collection of Event items.")
    droppedEventsCount: Optional[int] = Field(
        None,
        description=(
            "dropped_events_count is the number of dropped events. If the value is 0, then no events were dropped."
        ),
    )


class ScopeSpans(BaseModel):
    """A collection of Spans produced by an InstrumentationScope."""

    scope: Optional[InstrumentationScope] = Field(
        None,
        description=(
            "The instrumentation scope information for the spans in this message. Semantically when InstrumentationScope "
            "isn't set, it is equivalent with an empty instrumentation scope name (unknown)."
        ),
    )
    spans: list[Span] = Field(..., description="A list of Spans that originate from an instrumentation scope.")
    schemaUrl: Optional[str] = Field(
        None,
        description=(
            "The Schema URL, if known. This is the identifier of the Schema that the span data is recorded in. To learn more about Schema URL see "
            'https://opentelemetry.io/docs/specs/otel/schemas/#schema-url This schema_url applies to all spans and span events in the "spans" field.'
        ),
    )


class ResourceSpans(BaseModel):
    """A collection of ScopeSpans from a Resource."""

    resource: Optional[Resource] = Field(
        None,
        description=(
            "The resource for the spans in this message. If this field is not set then no resource info is known."
        ),
    )
    scopeSpans: list[ScopeSpans] = Field(..., description="A list of ScopeSpans that originate from a resource.")
    schemaUrl: Optional[str] = Field(
        None,
        description=(
            "The Schema URL, if known. This is the identifier of the Schema that the resource data is recorded in. To learn more about Schema URL see "
            'https://opentelemetry.io/docs/specs/otel/schemas/#schema-url This schema_url applies to the data in the "resource" field. It does not apply '
            'to the data in the "scope_spans" field which have their own schema_url field.'
        ),
    )


class TracesData(BaseModel):
    """TracesData represents the traces data that can be stored in a persistent storage,
    OR can be embedded by other protocols that transfer OTLP traces data but do
    not implement the OTLP protocol.

    The main difference between this message and collector protocol is that
    in this message there will not be any "control" or "metadata" specific to
    OTLP protocol.

    When new fields are added into this message, the OTLP request MUST be updated
    as well."""

    resourceSpans: list[ResourceSpans] = Field(
        ...,
        description=(
            "An array of ResourceSpans. For data coming from a single resource this array will typically contain one element. "
            "Intermediary nodes that receive data from multiple origins typically batch the data before forwarding further and "
            "in that case this array will contain multiple elements."
        ),
    )


class BatchesData(BaseModel):
    batches: list[ResourceSpans]
