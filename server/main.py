import asyncio
import json
from datetime import date
from typing import Annotated, AsyncIterable, Literal
from uuid import uuid4

from anyio import create_memory_object_stream
from devtools import debug
from pydantic import BaseModel, Discriminator, TypeAdapter, ValidationError
from pydantic.alias_generators import to_camel
from pydantic_ai import Agent, RunContext, messages as msgs
from sse_starlette.sse import EventSourceResponse
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

import vercel_ai_types as ai


class SubmitMessage(BaseModel, alias_generator=to_camel):
    trigger: Literal['submit-message']
    id: str
    messages: list[ai.UIMessage]

    model: str
    web_search: bool


class RegenerateMessage(BaseModel, alias_generator=to_camel):
    trigger: Literal['regenerate-message']
    id: str
    messages: list[ai.UIMessage]
    message_id: str


request_data_schema: TypeAdapter[SubmitMessage | RegenerateMessage] = TypeAdapter(
    Annotated[SubmitMessage | RegenerateMessage, Discriminator('trigger')]
)


class Person(BaseModel):
    name: str
    age: int
    dob: date
    lat: float
    lon: float


agent = Agent(
    'openai:gpt-4.1',
    # output_type=Person,
)


@agent.tool_plain
def get_lat_lon(location: str) -> dict[str, float]:
    return {'lat': 52.5200, 'lon': 13.4050}


async def chat_stream(user_prompt: str):
    message_id = uuid4().hex
    send_stream, receive_stream = create_memory_object_stream[ai.UIMessageChunk]()

    async def send(chunk: ai.UIMessageChunk):
        await send_stream.send(chunk)

    async def event_stream_handler(_deps: RunContext[None], events: AsyncIterable[msgs.AgentStreamEvent]) -> None:
        await send(ai.StartChunk())
        final_result_tool_id: str | None = None
        async for event in events:
            match event:
                case msgs.PartStartEvent(part=part):
                    match part:
                        case msgs.TextPart(content=content):
                            await send(ai.TextStartChunk(id=message_id))
                            await send(ai.TextDeltaChunk(id=message_id, delta=content))
                        case (
                            msgs.ToolCallPart(tool_name=tool_name, tool_call_id=tool_call_id, args=args)
                            | msgs.BuiltinToolCallPart(tool_name=tool_name, tool_call_id=tool_call_id, args=args)
                        ):
                            await send(ai.ToolInputStartChunk(tool_call_id=tool_call_id, tool_name=tool_name))
                            if isinstance(args, str):
                                await send(ai.ToolInputDeltaChunk(tool_call_id=tool_call_id, input_text_delta=args))
                            elif args is not None:
                                await send(
                                    ai.ToolInputDeltaChunk(tool_call_id=tool_call_id, input_text_delta=json.dumps(args))
                                )

                        case msgs.BuiltinToolReturnPart(
                            tool_name=tool_name, tool_call_id=tool_call_id, content=content
                        ):
                            await send(ai.ToolOutputAvailableChunk(tool_call_id=tool_call_id, output=content))

                        case msgs.ThinkingPart(content=content):
                            await send(ai.ReasoningStartChunk(id=message_id))
                            await send(ai.ReasoningDeltaChunk(id=message_id, delta=content))

                case msgs.PartDeltaEvent(delta=delta):
                    match delta:
                        case msgs.TextPartDelta(content_delta=content_delta):
                            await send(ai.TextDeltaChunk(id=message_id, delta=content_delta))
                        case msgs.ThinkingPartDelta(content_delta=content_delta):
                            if content_delta:
                                await send(ai.ReasoningDeltaChunk(id=message_id, delta=content_delta))
                        case msgs.ToolCallPartDelta(args_delta=args, tool_call_id=tool_call_id):
                            tool_call_id = tool_call_id or ''
                            if isinstance(args, str):
                                await send(ai.ToolInputDeltaChunk(tool_call_id=tool_call_id, input_text_delta=args))
                            elif args is not None:
                                await send(
                                    ai.ToolInputDeltaChunk(tool_call_id=tool_call_id, input_text_delta=json.dumps(args))
                                )
                case msgs.FinalResultEvent(tool_name=tool_name, tool_call_id=tool_call_id):
                    if tool_call_id and tool_name:
                        final_result_tool_id = tool_call_id
                        await send(ai.ToolInputStartChunk(tool_call_id=tool_call_id, tool_name=tool_name))
                case msgs.FunctionToolCallEvent():
                    pass
                    # print(f'TODO FunctionToolCallEvent {part}')
                case msgs.FunctionToolResultEvent(result=result):
                    match result:
                        case msgs.ToolReturnPart(tool_name=tool_name, tool_call_id=tool_call_id, content=content):
                            await send(ai.ToolOutputAvailableChunk(tool_call_id=tool_call_id, output=content))
                        case msgs.RetryPromptPart(tool_name=tool_name, tool_call_id=tool_call_id, content=content):
                            await send(ai.ToolOutputAvailableChunk(tool_call_id=tool_call_id, output=content))
                case msgs.BuiltinToolCallEvent(part=part):
                    tool_call_id = part.tool_call_id
                    tool_name = part.tool_name
                    args = part.args
                    await send(ai.ToolInputStartChunk(tool_call_id=tool_call_id, tool_name=tool_name))
                    if isinstance(args, str):
                        await send(ai.ToolInputDeltaChunk(tool_call_id=tool_call_id, input_text_delta=args))
                    elif args is not None:
                        await send(ai.ToolInputDeltaChunk(tool_call_id=tool_call_id, input_text_delta=json.dumps(args)))
                case msgs.BuiltinToolResultEvent(result=result):
                    await send(ai.ToolOutputAvailableChunk(tool_call_id=result.tool_call_id, output=result.content))

        if final_result_tool_id:
            await send(ai.ToolOutputAvailableChunk(tool_call_id=final_result_tool_id, output=None))
        await send(ai.FinishChunk())

    async def run_agent():
        await agent.run(user_prompt, event_stream_handler=event_stream_handler)
        send_stream.close()

    task = asyncio.create_task(run_agent())

    async for message in receive_stream:
        yield message

    await task


async def text_response(message_id: str, text: str) -> AsyncIterable[ai.UIMessageChunk]:
    yield ai.StartChunk()

    yield ai.StartStepChunk()
    yield ai.ReasoningStartChunk(id=message_id)
    yield ai.ReasoningDeltaChunk(id=message_id, delta=text)
    yield ai.FinishStepChunk()

    yield ai.FinishChunk()


async def sse_messages(messages_stream: AsyncIterable[ai.UIMessageChunk]) -> AsyncIterable[str]:
    async for message in messages_stream:
        yield message.model_dump_json(exclude_none=True, by_alias=True)
    # this doesn't seem to be necessary, but the next js app sends it
    yield '[DONE]'


def response(messages_stream: AsyncIterable[ai.UIMessageChunk]) -> EventSourceResponse:
    return EventSourceResponse(
        sse_messages(messages_stream),
        headers={'x-vercel-ai-ui-message-stream': 'v1'},
    )


async def chat_endpoint(request: Request) -> Response:
    body = await request.body()
    try:
        data = request_data_schema.validate_json(body)
    except ValidationError as e:
        debug(e)
        return JSONResponse({'errors': e.errors()}, status_code=422)

    message_id = uuid4().hex
    if not data.messages:
        return response(text_response(message_id, 'Error: no messages provided'))

    message = data.messages[-1]
    prompt: list[str] = []
    for part in message.parts:
        if isinstance(part, ai.TextUIPart):
            prompt.append(part.text)
        else:
            return response(text_response(message_id, 'Error: only text parts are supported yet'))

    return EventSourceResponse(
        sse_messages(chat_stream('\n'.join(prompt))),
        headers={'x-vercel-ai-ui-message-stream': 'v1'},
    )


routes = [
    Route('/api/chat', chat_endpoint, methods=['POST']),
]

app = Starlette(routes=routes)


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=8000)
