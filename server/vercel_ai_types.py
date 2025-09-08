"""
Convert to Python from

https://github.com/vercel/ai/blob/ai%405.0.34/packages/ai/src/ui/ui-messages.ts

Mostly with Claude.
"""

from typing import Any, Literal

from pydantic import BaseModel
from pydantic.alias_generators import to_camel

# technicall this is recursive union of JSON types
# for to simplify validation, we call it Any
JSONValue = Any

# Provider metadata types
ProviderMetadata = dict[str, dict[str, JSONValue]]


class UITool(BaseModel):
    input: Any
    output: Any | None = None


UITools = dict[str, UITool]


class CamelBaseModel(BaseModel, alias_generator=to_camel, populate_by_name=True, extra='forbid'):
    pass


class TextUIPart(CamelBaseModel):
    """A text part of a message."""

    type: Literal['text'] = 'text'

    text: str
    """The text content."""

    state: Literal['streaming', 'done'] | None = None
    """The state of the text part."""

    provider_metadata: ProviderMetadata | None = None
    """The provider metadata."""


class ReasoningUIPart(CamelBaseModel):
    """A reasoning part of a message."""

    type: Literal['reasoning'] = 'reasoning'

    text: str
    """The reasoning text."""

    state: Literal['streaming', 'done'] | None = None
    """The state of the reasoning part."""

    provider_metadata: ProviderMetadata | None = None
    """The provider metadata."""


class SourceUrlUIPart(CamelBaseModel):
    """A source part of a message."""

    type: Literal['source-url'] = 'source-url'
    source_id: str
    url: str
    title: str | None = None
    provider_metadata: ProviderMetadata | None = None


class SourceDocumentUIPart(CamelBaseModel):
    """A document source part of a message."""

    type: Literal['source-document'] = 'source-document'
    source_id: str
    media_type: str
    title: str
    filename: str | None = None
    provider_metadata: ProviderMetadata | None = None


class FileUIPart(CamelBaseModel):
    """A file part of a message."""

    type: Literal['file'] = 'file'

    media_type: str
    """
    IANA media type of the file.

    @see https://www.iana.org/assignments/media-types/media-types.xhtml
    """

    filename: str | None = None
    """Optional filename of the file."""

    url: str
    """
    The URL of the file.
    It can either be a URL to a hosted file or a [Data URL](https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/Data_URLs).
    """

    provider_metadata: ProviderMetadata | None = None
    """The provider metadata."""


class StepStartUIPart(CamelBaseModel):
    """A step boundary part of a message."""

    type: Literal['step-start'] = 'step-start'


UIDataTypes = dict[str, Any]


class DataUIPart(CamelBaseModel):
    """Data part with dynamic type based on data name."""

    type: str  # Will be f"data-{NAME}"
    id: str | None = None
    data: Any


# Tool part states as separate models
class ToolInputStreamingPart(CamelBaseModel):
    """Tool part in input-streaming state."""

    type: str  # Will be f"tool-{NAME}"
    tool_call_id: str
    state: Literal['input-streaming'] = 'input-streaming'
    input: Any | None = None
    provider_executed: bool | None = None


class ToolInputAvailablePart(CamelBaseModel):
    """Tool part in input-available state."""

    type: str  # Will be f"tool-{NAME}"
    tool_call_id: str
    state: Literal['input-available'] = 'input-available'
    input: Any
    provider_executed: bool | None = None
    call_provider_metadata: ProviderMetadata | None = None


class ToolOutputAvailablePart(CamelBaseModel):
    """Tool part in output-available state."""

    type: str  # Will be f"tool-{NAME}"
    tool_call_id: str
    state: Literal['output-available'] = 'output-available'
    input: Any
    output: Any
    provider_executed: bool | None = None
    call_provider_metadata: ProviderMetadata | None = None
    preliminary: bool | None = None


class ToolOutputErrorPart(CamelBaseModel):
    """Tool part in output-error state."""

    type: str  # Will be f"tool-{NAME}"
    tool_call_id: str
    state: Literal['output-error'] = 'output-error'
    input: Any | None = None
    raw_input: Any | None = None
    error_text: str
    provider_executed: bool | None = None
    call_provider_metadata: ProviderMetadata | None = None


# Union of all tool part states
ToolUIPart = ToolInputStreamingPart | ToolInputAvailablePart | ToolOutputAvailablePart | ToolOutputErrorPart


# Dynamic tool part states as separate models
class DynamicToolInputStreamingPart(CamelBaseModel):
    """Dynamic tool part in input-streaming state."""

    type: Literal['dynamic-tool'] = 'dynamic-tool'
    tool_name: str
    tool_call_id: str
    state: Literal['input-streaming'] = 'input-streaming'
    input: Any | None = None


class DynamicToolInputAvailablePart(CamelBaseModel):
    """Dynamic tool part in input-available state."""

    type: Literal['dynamic-tool'] = 'dynamic-tool'
    tool_name: str
    tool_call_id: str
    state: Literal['input-available'] = 'input-available'
    input: Any
    call_provider_metadata: ProviderMetadata | None = None


class DynamicToolOutputAvailablePart(CamelBaseModel):
    """Dynamic tool part in output-available state."""

    type: Literal['dynamic-tool'] = 'dynamic-tool'
    tool_name: str
    tool_call_id: str
    state: Literal['output-available'] = 'output-available'
    input: Any
    output: Any
    call_provider_metadata: ProviderMetadata | None = None
    preliminary: bool | None = None


class DynamicToolOutputErrorPart(CamelBaseModel):
    """Dynamic tool part in output-error state."""

    type: Literal['dynamic-tool'] = 'dynamic-tool'
    tool_name: str
    tool_call_id: str
    state: Literal['output-error'] = 'output-error'
    input: Any
    error_text: str
    call_provider_metadata: ProviderMetadata | None = None


# Union of all dynamic tool part states
DynamicToolUIPart = (
    DynamicToolInputStreamingPart
    | DynamicToolInputAvailablePart
    | DynamicToolOutputAvailablePart
    | DynamicToolOutputErrorPart
)


# Union of all message part types
UIMessagePart = (
    TextUIPart
    | ReasoningUIPart
    | ToolUIPart
    | DynamicToolUIPart
    | SourceUrlUIPart
    | SourceDocumentUIPart
    | FileUIPart
    | DataUIPart
    | StepStartUIPart
)


class UIMessage(CamelBaseModel):
    id: str
    """A unique identifier for the message."""

    role: Literal['system', 'user', 'assistant']
    """The role of the message."""

    metadata: Any | None = None
    """The metadata of the message."""

    parts: list[UIMessagePart]
    """
    The parts of the message. Use this for rendering the message in the UI.

    System messages should be avoided (set the system prompt on the server instead).
    They can have text parts.

    User messages can have text parts and file parts.

    Assistant messages can have text, reasoning, tool invocation, and file parts.
    """


class TextStartChunk(CamelBaseModel):
    """Text start chunk."""

    type: Literal['text-start'] = 'text-start'
    id: str
    provider_metadata: ProviderMetadata | None = None


class TextDeltaChunk(CamelBaseModel):
    """Text delta chunk."""

    type: Literal['text-delta'] = 'text-delta'
    delta: str
    id: str
    provider_metadata: ProviderMetadata | None = None


class TextEndChunk(CamelBaseModel):
    """Text end chunk."""

    type: Literal['text-end'] = 'text-end'
    id: str
    provider_metadata: ProviderMetadata | None = None


class ReasoningStartChunk(CamelBaseModel):
    """Reasoning start chunk."""

    type: Literal['reasoning-start'] = 'reasoning-start'
    id: str
    provider_metadata: ProviderMetadata | None = None


class ReasoningDeltaChunk(CamelBaseModel):
    """Reasoning delta chunk."""

    type: Literal['reasoning-delta'] = 'reasoning-delta'
    id: str
    delta: str
    provider_metadata: ProviderMetadata | None = None


class ReasoningEndChunk(CamelBaseModel):
    """Reasoning end chunk."""

    type: Literal['reasoning-end'] = 'reasoning-end'
    id: str
    provider_metadata: ProviderMetadata | None = None


class ErrorChunk(CamelBaseModel):
    """Error chunk."""

    type: Literal['error'] = 'error'
    error_text: str


class ToolInputAvailableChunk(CamelBaseModel):
    """Tool input available chunk."""

    type: Literal['tool-input-available'] = 'tool-input-available'
    tool_call_id: str
    tool_name: str
    input: Any
    provider_executed: bool | None = None
    provider_metadata: ProviderMetadata | None = None
    dynamic: bool | None = None


class ToolInputErrorChunk(CamelBaseModel):
    """Tool input error chunk."""

    type: Literal['tool-input-error'] = 'tool-input-error'
    tool_call_id: str
    tool_name: str
    input: Any
    provider_executed: bool | None = None
    provider_metadata: ProviderMetadata | None = None
    dynamic: bool | None = None
    error_text: str


class ToolOutputAvailableChunk(CamelBaseModel):
    """Tool output available chunk."""

    type: Literal['tool-output-available'] = 'tool-output-available'
    tool_call_id: str
    output: Any
    provider_executed: bool | None = None
    dynamic: bool | None = None
    preliminary: bool | None = None


class ToolOutputErrorChunk(CamelBaseModel):
    """Tool output error chunk."""

    type: Literal['tool-output-error'] = 'tool-output-error'
    tool_call_id: str
    error_text: str
    provider_executed: bool | None = None
    dynamic: bool | None = None


class ToolInputStartChunk(CamelBaseModel):
    """Tool input start chunk."""

    type: Literal['tool-input-start'] = 'tool-input-start'
    tool_call_id: str
    tool_name: str
    provider_executed: bool | None = None
    dynamic: bool | None = None


class ToolInputDeltaChunk(CamelBaseModel):
    """Tool input delta chunk."""

    type: Literal['tool-input-delta'] = 'tool-input-delta'
    tool_call_id: str
    input_text_delta: str


# Source chunk types
class SourceUrlChunk(CamelBaseModel):
    """Source URL chunk."""

    type: Literal['source-url'] = 'source-url'
    source_id: str
    url: str
    title: str | None = None
    provider_metadata: ProviderMetadata | None = None


class SourceDocumentChunk(CamelBaseModel):
    """Source document chunk."""

    type: Literal['source-document'] = 'source-document'
    source_id: str
    media_type: str
    title: str
    filename: str | None = None
    provider_metadata: ProviderMetadata | None = None


class FileChunk(CamelBaseModel):
    """File chunk."""

    type: Literal['file'] = 'file'
    url: str
    media_type: str


class DataUIMessageChunk(CamelBaseModel):
    """Data UI message chunk with dynamic type."""

    type: str  # Will be f"data-{NAME}"
    data: Any


class StartStepChunk(CamelBaseModel):
    """Start step chunk."""

    type: Literal['start-step'] = 'start-step'


class FinishStepChunk(CamelBaseModel):
    """Finish step chunk."""

    type: Literal['finish-step'] = 'finish-step'


# Message lifecycle chunk types
class StartChunk(CamelBaseModel):
    """Start chunk."""

    type: Literal['start'] = 'start'
    message_id: str | None = None
    message_metadata: Any | None = None


class FinishChunk(CamelBaseModel):
    """Finish chunk."""

    type: Literal['finish'] = 'finish'
    message_metadata: Any | None = None


class AbortChunk(CamelBaseModel):
    """Abort chunk."""

    type: Literal['abort'] = 'abort'


class MessageMetadataChunk(CamelBaseModel):
    """Message metadata chunk."""

    type: Literal['message-metadata'] = 'message-metadata'
    message_metadata: Any


# Union of all message chunk types
UIMessageChunk = (
    TextStartChunk
    | TextDeltaChunk
    | TextEndChunk
    | ReasoningStartChunk
    | ReasoningDeltaChunk
    | ReasoningEndChunk
    | ErrorChunk
    | ToolInputAvailableChunk
    | ToolInputErrorChunk
    | ToolOutputAvailableChunk
    | ToolOutputErrorChunk
    | ToolInputStartChunk
    | ToolInputDeltaChunk
    | SourceUrlChunk
    | SourceDocumentChunk
    | FileChunk
    | DataUIMessageChunk
    | StartStepChunk
    | FinishStepChunk
    | StartChunk
    | FinishChunk
    | AbortChunk
    | MessageMetadataChunk
)
