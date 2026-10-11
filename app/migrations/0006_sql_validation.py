from pathlib import Path
from django.db import migrations
class Migration(migrations.Migration):
    dependencies = [('app', '0005_configversion')]
    operations = [migrations.RunSQL((Path(__file__).resolve().parents[2] / 'sql/001_validation.sql').read_text())]
