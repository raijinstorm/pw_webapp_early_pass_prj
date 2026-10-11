from django.conf import settings
from django.db import transaction
from django.utils import timezone
from . import models as m

def user_role(user_id, product_id):
    user = m.User.objects.filter(pk=user_id, is_active=True).first()
    if not user:
        return None
    if user.is_superuser:
        return 'admin'
    if not hasattr(m, 'Membership'):
        return 'editor'
    return m.Membership.objects.filter(user_id=user_id, product_id=product_id).values_list('role', flat=True).first()

def product_by_id(product_id):
    return m.Product.objects.filter(pk=product_id).values().first()

def product_by_code(code):
    return m.Product.objects.filter(code=code).values().first()

def visible_products(user_id):
    return [dict(p, role=user_role(user_id, p['id']), config_count=m.Configuration.objects.filter(product_id=p['id']).count()) for p in m.Product.objects.values().order_by('name') if user_role(user_id, p['id'])]

def config_row(c):
    return dict(id=c.id, product_id=c.product_id, product_code=c.product.code, product_name=c.product.name, client_id=c.client_id, client_name=c.client.name, status=c.status, version=c.version, data=c.data, updated_at=c.updated_at, updated_by=c.updated_by.username if c.updated_by else None)

def configurations(user_id, product=None, client=None, status=None, search=None):
    qs = m.Configuration.objects.select_related('product', 'client', 'updated_by').order_by('product__name', 'client__name')
    if product: qs = qs.filter(product__code=product)
    if client: qs = qs.filter(client_id=client)
    if status: qs = qs.filter(status=status)
    if search: qs = qs.filter(client__name__icontains=search)
    return [config_row(c) for c in qs if user_role(user_id, c.product_id)]

def configuration(config_id):
    c = m.Configuration.objects.select_related('product', 'client', 'updated_by').filter(pk=config_id).first()
    return config_row(c) if c else None

def clients():
    return list(m.Client.objects.order_by('name').values('id', 'name'))

def clients_without_configuration(product_id):
    return list(m.Client.objects.exclude(id__in=m.Configuration.objects.filter(product_id=product_id).values('client_id')).order_by('name').values('id', 'name'))

def schema_fields(product_id):
    return list(m.SchemaField.objects.filter(product_id=product_id).order_by('position', 'key').values()) if hasattr(m, 'SchemaField') else []

def version_row(v):
    c = v.configuration
    return dict(id=v.id, configuration_id=c.id, number=v.number, is_current=v.number == c.version, data=v.data, comment=v.comment, created_at=v.created_at, author_id=v.author_id, author=v.author.username if v.author else None, product_id=c.product_id, product_code=c.product.code, product_name=c.product.name, client_name=c.client.name)

def versions(user_id, product=None, author=None, date_from=None, date_to=None, limit=None):
    if not hasattr(m, 'ConfigVersion'): return []
    qs = m.ConfigVersion.objects.select_related('configuration__product', 'configuration__client', 'author').order_by('-created_at', '-id')
    if product: qs = qs.filter(configuration__product__code=product)
    if author: qs = qs.filter(author__username=author)
    if date_from: qs = qs.filter(created_at__date__gte=date_from)
    if date_to: qs = qs.filter(created_at__date__lte=date_to)
    rows = [version_row(v) for v in qs if user_role(user_id, v.configuration.product_id)]
    return rows[:limit] if limit else rows

def history_authors(user_id):
    return [{'author': a} for a in sorted({v['author'] for v in versions(user_id) if v['author']})]

def configuration_versions(config_id):
    if not hasattr(m, 'ConfigVersion'): return []
    return [version_row(v) for v in m.ConfigVersion.objects.filter(configuration_id=config_id).select_related('configuration__product', 'configuration__client', 'author').order_by('-number')]

def version(version_id):
    v = m.ConfigVersion.objects.filter(pk=version_id).select_related('configuration__product', 'configuration__client', 'author').first()
    return version_row(v) if v else None

def version_changes(version_id):
    v = version(version_id)
    prev = m.ConfigVersion.objects.filter(configuration_id=v['configuration_id'], number=v['number']-1).first()
    old = prev.data if prev else {}
    return [{'key': k, 'old': old.get(k), 'new': v['data'].get(k)} for k in sorted(set(old) | set(v['data'])) if old.get(k) != v['data'].get(k)]

def create_configuration(product_id, client_id, data, author_id, comment):
    with transaction.atomic():
        c = m.Configuration.objects.create(product_id=product_id, client_id=client_id)
        save_version(c.id, data, author_id, comment)
        return c.id

def save_version(config_id, data, author_id, comment):
    from .db import fetch_all, as_jsonb
    from django.db import IntegrityError
    c = m.Configuration.objects.get(pk=config_id)
    problems = fetch_all('SELECT field_key, message FROM config_errors(%s, %s::jsonb)', [c.product_id, as_jsonb(data)])
    if problems:
        raise ValueError('; '.join(x['message'] for x in problems))
    c.version += 1
    c.data = data
    c.updated_by_id = author_id
    c.save()
    if hasattr(m, 'ConfigVersion'):
        m.ConfigVersion.objects.create(configuration_id=c.id, number=c.version, data=data, author_id=author_id, comment=comment, created_at=timezone.now())
    return c.version

def restore_version(version_id, author_id):
    v = version(version_id)
    return save_version(v['configuration_id'], v['data'], author_id, 'Restored version ' + str(v['number']))

def toggle_status(config_id):
    c = m.Configuration.objects.get(pk=config_id)
    c.status = 'disabled' if c.status == 'active' else 'active'
    c.save()
    return c.status

def members(product_id):
    if not hasattr(m, 'Membership'): return []
    return [dict(id=x.id, user_id=x.user_id, role=x.role, username=x.user.username, full_name=x.user.get_full_name()) for x in m.Membership.objects.filter(product_id=product_id).select_related('user')]
