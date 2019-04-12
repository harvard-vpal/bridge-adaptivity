from asgiref.sync import async_to_sync
import channels.layers
from channels.generic.websocket import AsyncWebsocketConsumer
import json

class NextButtonConsumer(AsyncWebsocketConsumer):

    prefix = 'activity'

    async def connect(self):
        self.room_name = f"{self.scope['url_route']['kwargs']['room_name']}"
        self.room_group_name = f'{self.prefix}_{self.room_name}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        pass

    async def chat_message(self, event):
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'result': message
        }))

    @staticmethod
    def send_message_to_channel(room_name, message):
        channel_layer = channels.layers.get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'{NextButtonConsumer.prefix}_{room_name}', {'type': 'chat_message', 'message': message}
        )
