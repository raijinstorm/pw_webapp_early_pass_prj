from pathlib import Path
from django.db import migrations
class Migration(migrations.Migration):
    dependencies = [('app', '0006_sql_validation')]
    operations = [migrations.RunSQL((Path(__file__).resolve().parents[2] / 'sql/002_install_versioning.sql').read_text()), migrations.RunSQL((Path(__file__).resolve().parents[2] / 'sql/003_access_and_reports.sql').read_text())]
