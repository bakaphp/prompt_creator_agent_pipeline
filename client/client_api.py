# Inside test_search_client.py or a new module
import os

from uuid import uuid4

import httpx
from fastapi import FastAPI
import uvicorn
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    MessageSendParams,
    SendStreamingMessageRequest,
)

async def run_search_client() -> dict:
    # (Your current logic goes here, but without asyncio.run())
    # Return useful info as JSON-safe dict instead of just printing
    results = []

    base_url = os.getenv('LOCAL_AGENT_ADDRESS', 'http://localhost:10002')

    async with httpx.AsyncClient() as httpx_client:
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)

        final_agent_card_to_use = None
        try:
            _public_card = await resolver.get_agent_card()
            final_agent_card_to_use = _public_card

            if (_public_card
                and hasattr(_public_card, "supportsAuthenticatedExtendedCard")
                and getattr(_public_card, "supportsAuthenticatedExtendedCard")):
                auth_headers_dict = {
                    'Authorization': 'Bearer dummy-token-for-extended-card'
                }
                _extended_card = await resolver.get_agent_card(
                    relative_card_path='/agent/authenticatedExtendedCard',
                    http_kwargs={'headers': auth_headers_dict},
                )
                final_agent_card_to_use = _extended_card

        except Exception as e:
            raise RuntimeError(
                f"Failed to fetch agent card: {e}"
            ) from e

        client = A2AClient(httpx_client=httpx_client, agent_card=final_agent_card_to_use)

        send_message_payload = {
            'message': {
                'role': 'user',
                'parts': [
                    {'kind': 'text', 'text': 'Lets create a prompt for a viral trend.'},
                ],
                'messageId': uuid4().hex,
            },
        }

        streaming_request = SendStreamingMessageRequest(
            id=str(uuid4()), params=MessageSendParams(**send_message_payload)
        )

        stream_response = client.send_message_streaming(streaming_request)

        async for chunk in stream_response:
            results.append(chunk.model_dump(mode='json', exclude_none=True))

    return {"message_chunks": results}


app = FastAPI()

@app.post("/run-client")
async def run_client_endpoint():
    print("Calling Prompt Creator Agent")
    result = await run_search_client()
    return result

if __name__ == "__main__":
    uvicorn.run("client_api:app", host=os.getenv("HOST","0.0.0.0"), port=os.getenv("PORT", 8080), reload=os.getenv("HOT_RELOAD", True))