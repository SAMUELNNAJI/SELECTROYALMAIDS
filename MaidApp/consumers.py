from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from .models import SupportMessage

class SupportConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        if not self.scope['user'].is_authenticated: await self.close(); return
        await self.channel_layer.group_add('support', self.channel_name); await self.accept()
    async def receive_json(self, content):
        body = str(content.get('body', '')).strip()
        if body: await self.channel_layer.group_send('support', {'type':'chat.message','message':await self.save(body)})
    async def chat_message(self, event): await self.send_json(event['message'])
    @database_sync_to_async
    def save(self, body):
        entry=SupportMessage.objects.create(sender=self.scope['user'],body=body)
        return {'sender':entry.sender.get_full_name() or entry.sender.username,'body':entry.body}
