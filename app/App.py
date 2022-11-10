from fastapi import FastAPI, Request, Response
from pydantic import BaseModel
from typing import List
import uvicorn
import httpx
import os
from datetime import datetime, timedelta

import chatbot

#uvicorn App:app --reload
#http://127.0.0.1:8000/docs#

# Request Models.
class WebhookRequestData(BaseModel):
    object: str = ""
    entry: List = []


# Helpers.
async def send_message(
    page_access_token: str,
    recipient_id: str,
    message: str,
    message_type: str = "RESPONSE",
):
    """
    Send message to specific user(By recipient ID) from specific page(By
    access token).
    Arguments:
        page_access_token: (string) Target page access token.
        recipient_id: (string) The ID of the user that the message is
         addressed to.
        message_text: (string) The content of the message.
        message_type: (string) The type of the target message.
         RESPONSE, UPDATE or MESSAGE_TAG - the accurate description -
         https://developers.facebook.com/docs/messenger-platform/send-messages/#messaging_types
    """
    r = httpx.post(
        "https://graph.facebook.com/v12.0/me/messages",
        params={"access_token": page_access_token},
        headers={"Content-Type": "application/json"},
        json={
            "recipient": {"id": recipient_id},
            "message": message,
            "messaging_type": message_type,
        },
    )
    r.raise_for_status()


# Init App.
app = FastAPI()


# Endpoints.
@app.router.get("/api/webhook")
async def verify(request: Request):
    """
    On webook verification VERIFY_TOKEN has to match the token at the
    configuration and send back "hub.challenge" as success.
    """
    if request.query_params.get("hub.mode") == "subscribe" and request.query_params.get(
        "hub.challenge"
    ):
        if (
            not request.query_params.get("hub.verify_token")
            == os.environ["VERIFY_TOKEN"]
        ):
            return Response(content="Verification token mismatch", status_code=403)
        return Response(content=request.query_params["hub.challenge"])

    return Response(content="Required arguments haven't passed.", status_code=400)


@app.router.post("/api/webhook")
async def webhook(data: WebhookRequestData):
    """
    Messages handler.
    """
    if data.object == "page":
        for entry in data.entry:
            messaging_events = [
                event for event in entry.get("messaging", []) if event.get("message")
            ]
            for event in messaging_events:
                if "text" in event.get("message"):
                    message = event.get("message")["text"]
                    senderid = event["sender"]["id"]
                    timestamp = datetime.fromtimestamp(event["timestamp"]/1e3) + timedelta(hours=2)

                    if 'quick_reply' in event.get("message").keys():
                        message = event.get("message")["quick_reply"]["payload"]

                    try:
                        response = chatbot.respond(message, senderid, timestamp)
                    except Exception as e:
                        response = {"text": f'The following error has occurred: "{e}". Take a screenshot of your last few messages and report this error to Kyana Bosschaerts. Try saying something again, or type "stop".'}

                    await send_message(page_access_token=os.environ["PAGE_ACCESS_TOKEN"],
                                    recipient_id=senderid,
                                    message=response)

    return Response(content="ok")


# Debug.
def main():
    #if "VERIFY_TOKEN" in os.environ:
    #    print("your verify token is: ", os.environ["VERIFY_TOKEN"])

    uvicorn.run(app=app)


if __name__ == "__main__":
    main()