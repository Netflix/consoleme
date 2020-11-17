import sys
import threading
from random import random
from typing import Dict, Optional

import aiozipkin as az
from pydantic import BaseModel

from consoleme.config import config

SERVER = "SERVER"
log = config.get_logger()


class ConsoleMeTracerObject(BaseModel):
    headers: Dict
    tracer: az.tracer.Tracer
    primary_span: az.tracer.Span

    class Config:
        arbitrary_types_allowed = True


class ConsoleMeTracer:
    def __init__(self):
        self.spans = {}
        self.headers = {}
        self.log_data = {}
        self.tracer = None
        self.primary_span = None

    def trace_calls(self, frame, event, arg):
        """
        Uses sys.settrace / threading.settrace hooks to create / finish Zipkin spans for function calls,
        exceptions, and returns. In a production environment, sys.settrace should be sampled.

        :param frame: Python Frame Object - https://docs.python.org/3/reference/datamodel.html#types
        :param event: A string describing the type of event (call, return, exception, etc) -
            https://docs.python.org/3/library/sys.html#sys.settrace
        :param arg: The return value or exception raised by the function, if relevant
        :return:
        """

        # Skip anything that's not a call, return, or exception
        if event not in ["call", "return", "exception"]:
            return

        # Set a reproducible pan name
        span_name = f"{frame.f_code.co_filename}-{frame.f_code.co_name}-{frame.f_back.f_code.co_filename}"

        # Skip tracing functions outside of core ConsoleMe by default
        in_scope_function_calls = config.get(
            "tracing.in_scope_function_calls", ["/consoleme/"]
        )
        if not (
            any(x in frame.f_code.co_filename for x in in_scope_function_calls)
            or any(
                x in frame.f_back.f_code.co_filename for x in in_scope_function_calls
            )
        ):
            if self.spans.get(span_name):
                self.spans[span_name].finish()
            return

        if self.spans.get(span_name):
            if event == "exception":
                if isinstance(arg[1], Exception) and arg[2]:  # Ensure traceback exists
                    self.spans.get(span_name).tag(
                        "error", arg[1]
                    )  # Record exception string as a tag
            self.spans[span_name].finish()
            return
        span = self.tracer.new_child(self.primary_span.context)  # Start a child span

        if event == "exception":
            if isinstance(arg[1], Exception) and arg[2]:  # Ensure traceback exists
                span.tag("error", arg[1])  # Record exception string as a tag

        span.kind(SERVER)
        span.start()
        span.name(frame.f_code.co_name)

        # Tag the span with context
        span.tag("FUNCTION", frame.f_code.co_name)
        span.tag("FUNCTION_LINE_NUM", frame.f_lineno)
        span.tag("FILENAME", frame.f_code.co_filename)
        span.tag("CALLER_FILENAME", frame.f_back.f_code.co_filename)
        span.tag("CALLER_LINE_NUM", frame.f_back.f_lineno)

        self.spans[span_name] = span
        frame.f_trace_lines = False
        frame.f_trace = self.trace_calls

    async def configure_tracing(
        self, span_name, span_kind=SERVER, tags=None, annotations=None
    ) -> Optional[ConsoleMeTracerObject]:
        if not config.get("tracing.enabled", False):
            return

        if not random() * 100 <= config.get("tracing.sample_rate", 0.1):  # nosec
            return

        if not tags:
            tags = []
        if not annotations:
            annotations = []
        zipkin_address = config.get(
            "tracing.zipkin_address", "http://127.0.0.1:9411/api/v2/spans"
        ).format(region=config.region, environment=config.get("environment"))
        endpoint = az.create_endpoint(
            config.get("tracing.application_name", "consoleme")
        )
        # The tracer's sample rate is 100% because we are pre-sampling our requests
        self.tracer = await az.create(zipkin_address, endpoint, sample_rate=1.0)
        self.primary_span = self.tracer.new_trace(sampled=True)
        self.headers = self.primary_span.context.make_headers()
        self.log_data = {
            "function": f"{__name__}.{self.__class__.__name__}.{sys._getframe().f_code.co_name}",
            "message": "Starting trace",
            "trace_id": self.primary_span.context.trace_id,
            "zipkin_address": zipkin_address,
            "tags": tags,
            "hostname": config.hostname,
        }
        log.debug(self.log_data)

        self.primary_span.kind(span_kind)
        self.primary_span.start()
        self.primary_span.name(span_name)
        self.primary_span.tag("HOSTNAME", config.hostname)

        for k, v in tags.items():
            self.primary_span.tag(k, v)
        for annotation in annotations:
            self.primary_span.annotate(annotation)

        # Configure sys/threading.settrace to use our trace_calls function for tracing
        # Note: This is expensive, and should definitely not run for every request
        sys.settrace(self.trace_calls)
        threading.settrace(self.trace_calls)
        return ConsoleMeTracerObject(
            primary_span=self.primary_span, tracer=self.tracer, headers=self.headers
        )

    async def disable_tracing(self):
        if not config.get("tracing.enabled", False):
            return
        self.log_data["message"] = "disabling tracing"
        log.debug(self.log_data)
        sys.settrace(None)
        threading.settrace(None)

    async def set_additional_tags(self, tags):
        if self.primary_span:
            for k, v in tags.items():
                self.primary_span.tag(k, v)

    async def finish_spans(self):
        """
        Closes all of the spans and the tracer. Our trace should be visible on ZipKin after this function
        completes.
        :return:
        """
        # Finish any nested spans that are still open.
        # We iterate through the dictionary of spans in a safe manner
        # to avoid a "Dictionary changed size during iteration" error as other asynchronous
        # callers modify self.spans
        if not config.get("tracing.enabled", False):
            return
        self.log_data["message"] = "finishing spans"
        log.debug(self.log_data)
        for span_id in list(self.spans):
            span = self.spans.get(span_id)
            if span:
                span.finish()

        # Finish primary span
        if self.primary_span:
            self.primary_span.finish()

        # Close the tracer
        if self.tracer:
            await self.tracer.close()
