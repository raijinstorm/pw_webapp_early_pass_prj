import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('app', '0003_schemafield')]
    operations = [migrations.CreateModel(name='Membership', fields=[('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('role', models.CharField(choices=[('manager', 'Manager'), ('editor', 'Editor')], default='editor', max_length=20)), ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='app.product')), ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to=settings.AUTH_USER_MODEL))], options={'db_table': 'membership', 'constraints': [models.UniqueConstraint(fields=('user', 'product'), name='membership_unique')]})]
