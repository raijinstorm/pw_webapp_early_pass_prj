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

def config_list(request):
    form = ConfigFilterForm(request.GET or None, user=request.user)
    f = filter_values(form)
    rows = queries.configurations(request.user.id, product=f.get('product'), client=f.get('client'), status=f.get('status'), search=f.get('q'))
    (page, querystring) = paginate(request, rows)
    context = {'form': form, 'page': page, 'querystring': querystring}
    template = 'app/partials/config_table.html' if is_htmx(request) else 'app/config_list.html'
    return render(request, template, context)

def history_list(request):
    form = HistoryFilterForm(request.GET or None, user=request.user)
    f = filter_values(form)
    rows = queries.versions(request.user.id, product=f.get('product'), author=f.get('author'), date_from=f.get('date_from'), date_to=f.get('date_to'))
    (page, querystring) = paginate(request, rows)
    context = {'form': form, 'page': page, 'querystring': querystring}
    template = 'app/partials/history_table.html' if is_htmx(request) else 'app/history_list.html'
    return render(request, template, context)

def product_detail(request, code):
    (product, role) = get_product(request.user, code)
    context = {'product': product, 'role': role, 'can_manage': role in MANAGER_ROLES, 'configs': queries.configurations(request.user.id, product=code), 'fields': queries.schema_fields(product['id']), 'memberships': queries.members(product['id']), 'member_form': MemberForm()}
    return render(request, 'app/product_detail.html', context)

def config_detail(request, pk):
    (configuration, product, role) = get_configuration(request.user, pk)
    fields = queries.schema_fields(product['id'])
    context = {'config': configuration, 'rows': [(f, configuration['data'].get(f['key'])) for f in fields], 'versions': queries.configuration_versions(pk), 'can_manage': role in MANAGER_ROLES}
    return render(request, 'app/config_detail.html', context)

def save_or_show_errors(form, write, error_messages=None):
    try:
        with transaction.atomic():
            return write()
    except IntegrityError as error:
        if not form.apply_db_error(error, error_messages):
            raise
        return None

def config_create(request, code):
    (product, _) = get_product(request.user, code)
    if not queries.schema_fields(product['id']):
        messages.warning(request, 'This product has no schema fields yet. A manager has to define them first.')
        return redirect('product_detail', code=code)
    form = ConfigForm(request.POST or None, product=product)
    if request.method == 'POST' and form.is_valid():
        config_id = save_or_show_errors(form, lambda : queries.create_configuration(product['id'], form.cleaned_data['client'], form.data_json(), request.user.id, form.cleaned_data['comment']))
        if config_id:
            messages.success(request, 'Configuration created.')
            return redirect('config_detail', pk=config_id)
    return render(request, 'app/config_form.html', {'form': form, 'product': product})

def config_edit(request, pk):
    (configuration, product, _) = get_configuration(request.user, pk)
    form = ConfigForm(request.POST or None, product=product, configuration=configuration)
    if request.method == 'POST' and form.is_valid():
        number = save_or_show_errors(form, lambda : queries.save_version(pk, form.data_json(), request.user.id, form.cleaned_data['comment']))
        if number:
            messages.success(request, f'Saved as version {number}.')
            return redirect('config_detail', pk=pk)
    return render(request, 'app/config_form.html', {'form': form, 'product': product, 'config': configuration})

def version_detail(request, pk):
    version = found(queries.version(pk))
    (_, role) = get_product(request.user, version['product_code'])
    context = {'version': version, 'changes': queries.version_changes(pk), 'can_manage': role in MANAGER_ROLES}
    return render(request, 'app/partials/version_detail.html', context)

@require_POST
def version_restore(request, pk):
    version = found(queries.version(pk))
    get_product(request.user, version['product_code'], manage=True)
    try:
        with transaction.atomic():
            number = queries.restore_version(pk, request.user.id)
        messages.success(request, f"Version {version['number']} restored as version {number}.")
    except IntegrityError as error:
        messages.error(request, f"Version {version['number']} can't be restored: {error.__cause__.diag.message_primary}")
    return redirect('config_detail', pk=version['configuration_id'])
