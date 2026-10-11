import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('app', '0004_membership')]
    operations = [migrations.CreateModel(name='ConfigVersion', fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('number', models.IntegerField()), ('data', models.JSONField()), ('comment', models.TextField()), ('created_at', models.DateTimeField(default=django.utils.timezone.now)), ('author', models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to=settings.AUTH_USER_MODEL)), ('configuration', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='app.configuration'))], options={'db_table': 'config_version', 'ordering': ['-created_at']})]
