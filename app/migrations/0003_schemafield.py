import django.contrib.postgres.fields
import django.db.models.deletion
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('app', '0002_client_product_configuration')]
    operations = [migrations.CreateModel(name='SchemaField', fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('key', models.CharField(max_length=50)), ('label', models.CharField(max_length=100)), ('field_type', models.CharField(max_length=20)), ('required', models.BooleanField(default=True)), ('min_value', models.DecimalField(blank=True, decimal_places=6, max_digits=20, null=True)), ('max_value', models.DecimalField(blank=True, decimal_places=6, max_digits=20, null=True)), ('choices', django.contrib.postgres.fields.ArrayField(base_field=models.TextField(), blank=True, null=True, size=None)), ('pattern', models.TextField(blank=True, null=True)), ('help_text', models.TextField(blank=True, default='')), ('position', models.IntegerField(default=0)), ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fields', to='app.product'))], options={'db_table': 'schema_field'})]
