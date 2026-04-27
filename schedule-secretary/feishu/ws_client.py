"""
Feishu WebSocket Client for Schedule Secretary
Uses Feishu SDK long connection mode
"""
import os
import json
import threading
import time
from lark_oapi.ws.client import Client
from lark_oapi.event.dispatcher_handler import EventDispatcherHandlerBuilder
from lark_oapi.api.im.v1.model.p2_im_message_receive_v1 import P2ImMessageReceiveV1

from dotenv import load_dotenv
load_dotenv()

FEISHU_APP_ID = os.getenv("FEISHU_APP_ID")
FEISHU_APP_SECRET = os.getenv("FEISHU_APP_SECRET")

# Encrypt and verification keys (can be empty for long connection)
ENCRYPT_KEY = ""
VERIFICATION_TOKEN = ""


class FeishuWSClient:
    """Feishu WebSocket client for receiving and handling messages"""

    def __init__(self):
        self.app_id = FEISHU_APP_ID
        self.app_secret = FEISHU_APP_SECRET
        self.client = None
        self._running = False
        self._thread = None

    def start(self):
        """Start the WebSocket client"""
        if self._running:
            print("[FeishuWS] Already running")
            return

        self._running = True

        # Build event dispatcher
        builder = EventDispatcherHandlerBuilder(ENCRYPT_KEY, VERIFICATION_TOKEN)
        builder.register_p2_im_message_receive_v1(self._handle_message_v1)
        event_handler = builder.build()

        # Create WebSocket client
        self.client = Client(
            self.app_id,
            self.app_secret,
            event_handler=event_handler
        )

        # Start in a separate thread
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print("[FeishuWS] WebSocket client started")

    def _run(self):
        """Run the client"""
        try:
            self.client.start()
        except Exception as e:
            print(f"[FeishuWS] Error: {e}")
        finally:
            self._running = False

    def stop(self):
        """Stop the WebSocket client"""
        self._running = False
        print("[FeishuWS] Client stopped")

    def _handle_message_v1(self, data: P2ImMessageReceiveV1) -> None:
        """Handle incoming messages"""
        try:
            print(f"[FeishuWS] Received event type: {type(data)}")

            # Get event property (contains message and sender)
            event = data.event if hasattr(data, 'event') else None
            if not event:
                print("[FeishuWS] No event in data")
                return

            print(f"[FeishuWS] Event type: {type(event)}")

            # Get message from event
            message = event.message if hasattr(event, 'message') else None
            sender = event.sender if hasattr(event, 'sender') else None

            if not message:
                print("[FeishuWS] No message in event")
                return

            # Get text content from message
            content_str = message.content if hasattr(message, 'content') else "{}"
            try:
                content = json.loads(content_str) if isinstance(content_str, str) else content_str
            except:
                content = {}

            text = content.get("text", "").strip() if isinstance(content, dict) else ""

            # Get sender open_id
            sender_id = ""
            sender_id_str = ""
            if sender:
                try:
                    sender_id_str = str(sender)
                    print(f"[FeishuWS] Sender: {sender_id_str[:200]}")
                except:
                    print("[FeishuWS] Sender: (can't convert to string)")
                sender_id_obj = sender.sender_id if hasattr(sender, 'sender_id') else None
                if sender_id_obj:
                    try:
                        sender_id_str = str(sender_id_obj)
                        print(f"[FeishuWS] sender_id_obj: {sender_id_str[:200]}")
                    except:
                        print("[FeishuWS] sender_id_obj: (can't convert)")
                    if hasattr(sender_id_obj, 'open_id'):
                        sender_id = sender_id_obj.open_id

            print(f"[FeishuWS] text=[{text}], sender_id=[{sender_id}]")

            if text:
                # Process command
                from feishu.bot import parse_command, handle_command, send_text_message
                command = parse_command(text)
                response = handle_command(command)
                try:
                    print(f"[FeishuWS] Response: {response}")
                except UnicodeEncodeError:
                    print(f"[FeishuWS] Response: (contains emoji)")

                # Send response back
                if sender_id:
                    try:
                        result = send_text_message(response, sender_id)
                        print(f"[FeishuWS] Send result: {result}")
                    except Exception as e:
                        print(f"[FeishuWS] Send failed: {e}")

        except Exception as e:
            print(f"[FeishuWS] Handler error: {e}")
            import traceback
            traceback.print_exc()


# Global client instance
_ws_client = None


def get_ws_client():
    """Get or create the global WebSocket client"""
    global _ws_client
    if _ws_client is None:
        _ws_client = FeishuWSClient()
    return _ws_client


def start_ws_client():
    """Start the WebSocket client"""
    client = get_ws_client()
    client.start()
    return client


if __name__ == "__main__":
    print("Starting Feishu WebSocket client...")
    start_ws_client()
    print("Press Ctrl+C to stop")
    while True:
        time.sleep(1)
