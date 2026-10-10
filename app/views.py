from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from . import queries
from .forms import MEMBER_ERRORS, SCHEMA_FIELD_ERRORS, ConfigFilterForm, ConfigForm, HistoryFilterForm, MemberForm, SchemaFieldForm
PAGE_SIZE = 15
MANAGER_ROLES = ('admin', 'manager')

def is_htmx(request):
    return request.headers.get('HX-Request') == 'true'

def found(row):
    if row is None:
        raise Http404
    return row

def get_product(user, code, manage=False):
    product = found(queries.product_by_code(code))
    role = queries.user_role(user.id, product['id'])
    if role is None or (manage and role not in MANAGER_ROLES):
        raise PermissionDenied
    return (product, role)

def get_configuration(user, config_id, manage=False):
    configuration = found(queries.configuration(config_id))
    (product, role) = get_product(user, configuration['product_code'], manage=manage)
    return (configuration, product, role)

def filter_values(form):
    if not form.is_bound:
        return {}
    form.is_valid()
    return {k: v if v not in ('', None) else None for (k, v) in form.cleaned_data.items()}

def paginate(request, rows):
    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get('page'))
    params = request.GET.copy()
    params.pop('page', None)
    return (page, params.urlencode())

def dashboard(request):
    context = {'products': queries.visible_products(request.user.id), 'recent': queries.versions(request.user.id, limit=8)}
    return render(request, 'app/dashboard.html', context)

def product_detail(request, code):
    (product, role) = get_product(request.user, code)
    context = {'product': product, 'role': role, 'can_manage': role in MANAGER_ROLES, 'configs': queries.configurations(request.user.id, product=code), 'fields': queries.schema_fields(product['id']), 'memberships': queries.members(product['id']), 'member_form': MemberForm()}
    return render(request, 'app/product_detail.html', context)

def config_detail(request, pk):
    (configuration, product, role) = get_configuration(request.user, pk)
    fields = queries.schema_fields(product['id'])
    context = {'config': configuration, 'rows': [(f, configuration['data'].get(f['key'])) for f in fields], 'versions': queries.configuration_versions(pk), 'can_manage': role in MANAGER_ROLES}
    return render(request, 'app/config_detail.html', context)
