import os
from django.core.management.base import BaseCommand
from app.models import User, Product, Client, Configuration
class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        if User.objects.exists(): return
        u = User.objects.create_superuser('admin', 'admin@confighub.example.com', os.environ['DEMO_PASSWORD'])
        p = Product.objects.create(code='pricing-feed', name='Pricing Feed', description='Daily pricing settings')
        c = Client.objects.create(name='Acme')
        Configuration.objects.create(product=p, client=c, data={'refresh_hours':6, 'currency':'EUR'}, updated_by=u)
