import asyncio
from typing import Annotated, AsyncIterable, Literal
from uuid import uuid4

from devtools import debug
from pydantic import BaseModel, Discriminator, TypeAdapter, ValidationError
from pydantic.alias_generators import to_camel
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


async def message_generator() -> AsyncIterable[ai.UIMessageChunk]:
    message_id = uuid4().hex

    yield ai.StartChunk()
    yield ai.StartStepChunk()
    yield ai.TextStartChunk(id=message_id, provider_metadata={'openai': {'itemId': message_id}})
    yield ai.TextDeltaChunk(id=message_id, delta='Hi')
    yield ai.TextDeltaChunk(id=message_id, delta=' again')
    yield ai.TextDeltaChunk(id=message_id, delta='!')
    yield ai.TextDeltaChunk(id=message_id, delta=' 😊')
    yield ai.TextDeltaChunk(id=message_id, delta=' How')
    yield ai.TextDeltaChunk(id=message_id, delta=' can')
    yield ai.TextDeltaChunk(id=message_id, delta=' I')
    yield ai.TextDeltaChunk(id=message_id, delta=' assist')
    yield ai.TextDeltaChunk(id=message_id, delta=' you')
    yield ai.TextDeltaChunk(id=message_id, delta=' today')
    yield ai.TextDeltaChunk(id=message_id, delta='?')
    yield ai.TextDeltaChunk(id=message_id, delta=message_id)
    yield ai.TextEndChunk(id=message_id)
    yield ai.FinishStepChunk()
    yield ai.FinishChunk()


async def sse_messages(messages_stream: AsyncIterable[ai.UIMessageChunk]) -> AsyncIterable[str]:
    async for message in messages_stream:
        yield message.model_dump_json(exclude_none=True, by_alias=True)
        await asyncio.sleep(0.1)


async def chat_endpoint(request: Request) -> Response:
    body = await request.body()
    print(body)
    try:
        data = request_data_schema.validate_json(body)
    except ValidationError as e:
        debug(e)
        return JSONResponse({'errors': e.errors()}, status_code=422)
    debug(data)
    return EventSourceResponse(
        sse_messages(message_generator()),
        headers={'x-vercel-ai-ui-message-stream': 'v1'},
    )


routes = [
    Route('/api/chat', chat_endpoint, methods=['POST']),
]

app = Starlette(routes=routes)


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=8000)
