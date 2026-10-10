from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe
register = template.Library()

@register.filter
def show(value):
    if value is None or value == '':
        return mark_safe('<span class="text-body-tertiary">—</span>')
    if value is True:
        return mark_safe('<span class="badge text-bg-success">Yes</span>')
    if value is False:
        return mark_safe('<span class="badge text-bg-secondary">No</span>')
    return value

@register.filter
def role_badge(role):
    colors = {'admin': 'danger', 'manager': 'primary', 'editor': 'info'}
    if not role:
        return ''
    return format_html('<span class="badge text-bg-{}">{}</span>', colors.get(role, 'secondary'), str(role).title())

@register.filter
def bootstrap(field):
    if 'class' in field.field.widget.attrs:
        return field
    css = {'checkbox': 'form-check-input', 'select': 'form-select'}.get(field.widget_type, 'form-control')
    if field.errors:
        css += ' is-invalid'
    return field.as_widget(attrs={'class': css})
