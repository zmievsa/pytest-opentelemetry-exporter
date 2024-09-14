from typing import Any, Optional, TypedDict

from pytest_opentelemetry_exporter.types import BatchesData, KeyValue, SpanKind


def get_attribute(attributes: list[KeyValue], key: str) -> Any:
    """
    Retrieve the value for a given key from the list of attributes.
    Handles different value types: stringValue, intValue, doubleValue.
    """
    for attr in attributes:
        if attr["key"] == key:
            value = attr["value"]
            if "stringValue" in value:
                return value["stringValue"]
            elif "intValue" in value:
                return int(value["intValue"])
            elif "doubleValue" in value:
                return float(value["doubleValue"])
    return None


class BusinessHttpRequest(TypedDict):
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    service_name: Optional[str]
    span_name: str
    kind: Optional[SpanKind]
    start_time_unix_nano: int
    end_time_unix_nano: int
    http_method: Optional[str]
    http_url: Optional[str]
    http_status_code: Optional[int]


def extract_business_http_requests(data: BatchesData) -> list[BusinessHttpRequest]:
    """
    Returns:
        list: A list of dictionaries containing extracted HTTP request details.
    """
    business_http_requests: list[BusinessHttpRequest] = []

    # Iterate through each batch
    for batch in data["batches"]:
        resource = batch.get("resource", {})
        attributes = resource.get("attributes", {})

        # Get the service name
        service_name = get_attribute(attributes, "service.name")

        # Skip batches related to Kong
        if service_name == "kong":
            continue

        # Iterate through scopeSpans
        for scope_span in batch.get("scopeSpans"):
            spans = scope_span.get("spans")

            for span in spans:
                span_attributes = span.get("attributes", [])

                # Check if the span has an HTTP method attribute
                http_method = get_attribute(span_attributes, "http.method")
                if not http_method:
                    continue  # Skip non-HTTP spans

                # Extract relevant HTTP attributes
                http_url: str = get_attribute(span_attributes, "http.url")
                http_status_code: int = get_attribute(span_attributes, "http.status_code")

                # Extract additional span details
                trace_id = span.get("traceId")
                span_id = span.get("spanId")
                parent_span_id = span.get("parentSpanId")
                name = span.get("name")
                kind = span.get("kind")
                start_time = span.get("startTimeUnixNano")
                end_time = span.get("endTimeUnixNano")

                # We only care about spans that receive requests, not the spans that send them
                if kind != "SPAN_KIND_SERVER":
                    continue

                # Append the extracted information to the list
                business_http_requests.append(
                    {
                        "trace_id": trace_id,
                        "span_id": span_id,
                        "parent_span_id": parent_span_id,
                        "service_name": service_name,
                        "span_name": name,
                        "kind": kind,
                        "start_time_unix_nano": start_time,
                        "end_time_unix_nano": end_time,
                        "http_method": http_method,
                        "http_url": http_url,
                        "http_status_code": http_status_code,
                    }
                )

    return business_http_requests
