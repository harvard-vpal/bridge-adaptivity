import json


from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncWebsocketConsumer
import channels.layers


class CallbackSequenceConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.sequence_item_channel = f"{self.scope['url_route']['kwargs']['sequence_item']}"
        self.sequence_item_group = f"group_{self.sequence_item_channel}"

        await self.channel_layer.group_add(
            self.sequence_item_group,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.sequence_item_group,
            self.channel_name
        )

    async def send_message(self, event):
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'result': message
        }))

    @staticmethod
    def send_message_to_channel(sequence_item_channel, message):
        channel_layer = channels.layers.get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'group_{sequence_item_channel}', {'type': 'send_message', 'message': message}
        )
