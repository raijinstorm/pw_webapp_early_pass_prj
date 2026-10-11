import json
from datetime import date
from decimal import Decimal
from django import forms
from . import queries
from .db import db_error
from .models import Role
VALUE_PREFIX = 'value__'
FIELD_TYPES = [('text', 'Text'), ('integer', 'Integer'), ('decimal', 'Decimal'), ('boolean', 'Yes / No'), ('date', 'Date'), ('choice', 'Choice')]
STATUSES = [('active', 'Active'), ('disabled', 'Disabled')]

class BootstrapFormMixin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.style_fields()

    def style_fields(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css = 'form-check-input'
            elif isinstance(widget, forms.Select):
                css = 'form-select'
            else:
                css = 'form-control'
            widget.attrs['class'] = css

    def mark_invalid(self):
        for name in self.errors:
            if name in self.fields and 'is-invalid' not in self.fields[name].widget.attrs['class']:
                self.fields[name].widget.attrs['class'] += ' is-invalid'

    def is_valid(self):
        valid = super().is_valid()
        self.mark_invalid()
        return valid

    def apply_db_error(self, error, messages):
        (constraint, _) = db_error(error)
        if constraint not in messages:
            return False
        (field, text) = messages[constraint]
        self.add_error(field, text)
        self.mark_invalid()
        return True

def value_field(f):
    attrs = {}
    if f['required']:
        attrs['required'] = True
    common = {'label': f['label'], 'help_text': f['help_text'], 'required': False}
    kind = f['field_type']
    if kind in ('integer', 'decimal'):
        if f['min_value'] is not None:
            attrs['min'] = f['min_value']
        if f['max_value'] is not None:
            attrs['max'] = f['max_value']
        if kind == 'integer':
            return forms.IntegerField(widget=forms.NumberInput(attrs=attrs), **common)
        attrs['step'] = 'any'
        return forms.DecimalField(widget=forms.NumberInput(attrs=attrs), **common)
    if kind == 'boolean':
        return forms.BooleanField(**common)
    if kind == 'date':
        return forms.DateField(widget=forms.DateInput(attrs={**attrs, 'type': 'date'}), **common)
    if kind == 'choice':
        options = [('', '---------')] + [(c, c) for c in f['choices']]
        return forms.ChoiceField(choices=options, widget=forms.Select(attrs=attrs), **common)
    return forms.CharField(widget=forms.TextInput(attrs=attrs), **common)

def to_json_value(value):
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if value == '':
        return None
    return value

class ConfigForm(BootstrapFormMixin, forms.Form):

    def __init__(self, *args, product, configuration=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.schema = queries.schema_fields(product['id'])
        if configuration is None:
            clients = queries.clients_without_configuration(product['id'])
            self.fields['client'] = forms.TypedChoiceField(choices=[('', '---------')] + [(c['id'], c['name']) for c in clients], coerce=int, help_text='Only clients without a configuration for this product are listed.')
        for f in self.schema:
            name = VALUE_PREFIX + f['key']
            self.fields[name] = value_field(f)
            if configuration is not None:
                self.initial[name] = configuration['data'].get(f['key'])
        self.fields['comment'] = forms.CharField(max_length=200, label='Change comment', help_text='Why are you making this change? Shown in the history.')
        self.style_fields()

    def value_fields(self):
        return [self[VALUE_PREFIX + f['key']] for f in self.schema]

    def data_json(self):
        return {f['key']: to_json_value(self.cleaned_data.get(VALUE_PREFIX + f['key'])) for f in self.schema}

    def apply_db_error(self, error, messages=None):
        (constraint, detail) = db_error(error)
        if constraint == 'config_data_matches_schema':
            for (key, text) in json.loads(detail).items():
                name = VALUE_PREFIX + key
                self.add_error(name if name in self.fields else None, text if name in self.fields else f'{key}: {text}')
            self.mark_invalid()
            return True
        return super().apply_db_error(error, CONFIG_ERRORS)
CONFIG_ERRORS = {'config_version_has_changes': (None, 'Nothing changed: there is no new version to save.'), 'configuration_product_client_unique': ('client', 'This client already has a configuration for this product.'), 'config_version_comment_not_blank': ('comment', 'Please describe the change.')}

class SchemaFieldForm(BootstrapFormMixin, forms.Form):
    key = forms.CharField(max_length=50, help_text='Lowercase letters, digits and underscores, e.g. refresh_hours.')
    label = forms.CharField(max_length=100)
    field_type = forms.ChoiceField(choices=FIELD_TYPES)
    required = forms.BooleanField(required=False, initial=True)
    min_value = forms.DecimalField(required=False)
    max_value = forms.DecimalField(required=False)
    choices = forms.CharField(required=False, max_length=500, help_text='Comma-separated options (Choice type only).')
    pattern = forms.CharField(required=False, max_length=200, help_text='Optional regular expression (Text type only).')
    help_text = forms.CharField(required=False, max_length=200)
    position = forms.IntegerField(initial=0)

    def __init__(self, *args, editing=False, **kwargs):
        super().__init__(*args, **kwargs)
        if editing:
            self.fields['key'].disabled = True
            self.fields['key'].help_text = "The key can't be changed once created."

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('field_type') == 'boolean':
            cleaned['required'] = False
        return cleaned

    def values(self):
        d = self.cleaned_data
        options = [c.strip() for c in d['choices'].split(',') if c.strip()]
        return {'key': d['key'], 'label': d['label'], 'field_type': d['field_type'], 'required': d['required'], 'min_value': d['min_value'], 'max_value': d['max_value'], 'choices': options or None, 'pattern': d['pattern'] or None, 'help_text': d['help_text'], 'position': d['position']}

    @staticmethod
    def initial_from_row(row):
        return {**row, 'choices': ', '.join(row['choices'] or []), 'pattern': row['pattern'] or ''}
SCHEMA_FIELD_ERRORS = {'schema_field_key_unique': ('key', 'This product already has a field with this key.'), 'schema_field_key_format': ('key', 'Use lowercase letters, digits and underscores, starting with a letter.'), 'schema_field_label_not_blank': ('label', "The label can't be blank."), 'schema_field_range_only_numeric': ('min_value', 'Min/max only apply to Integer and Decimal fields.'), 'schema_field_min_le_max': ('max_value', 'Max must be greater than or equal to min.'), 'schema_field_choices_only_choice': ('choices', 'Choice fields need options, and only Choice fields can have them.'), 'schema_field_choices_at_least_two': ('choices', 'Give at least two options.'), 'schema_field_pattern_only_text': ('pattern', 'A pattern only applies to Text fields.'), 'schema_field_pattern_valid': ('pattern', 'This is not a valid regular expression.'), 'schema_field_position_positive': ('position', "Position can't be negative.")}

class MemberForm(BootstrapFormMixin, forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'placeholder': 'Username', 'aria-label': 'Username'}))
    role = forms.ChoiceField(choices=Role.choices, initial=Role.EDITOR, widget=forms.Select(attrs={'aria-label': 'Role'}))

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        self.user_id = queries.active_user_id(username)
        if self.user_id is None:
            raise forms.ValidationError('No active user with this username.')
        return username
MEMBER_ERRORS = {'membership_unique': ('username', 'This user is already a member of the product.')}

class ConfigFilterForm(BootstrapFormMixin, forms.Form):
    q = forms.CharField(required=False, max_length=100, label='Search client', widget=forms.TextInput(attrs={'placeholder': 'Search client…'}))
    product = forms.ChoiceField(required=False)
    client = forms.TypedChoiceField(required=False, coerce=int, empty_value=None)
    status = forms.ChoiceField(choices=[('', 'Any status'), *STATUSES], required=False)

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        products = queries.visible_products(user.id)
        self.fields['product'].choices = [('', 'All products')] + [(p['code'], p['name']) for p in products]
        self.fields['client'].choices = [('', 'All clients')] + [(c['id'], c['name']) for c in queries.clients()]

class HistoryFilterForm(BootstrapFormMixin, forms.Form):
    product = forms.ChoiceField(required=False)
    author = forms.ChoiceField(required=False)
    date_from = forms.DateField(required=False, label='From', widget=forms.DateInput(attrs={'type': 'date'}))
    date_to = forms.DateField(required=False, label='To', widget=forms.DateInput(attrs={'type': 'date'}))

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        products = queries.visible_products(user.id)
        self.fields['product'].choices = [('', 'All products')] + [(p['code'], p['name']) for p in products]
        self.fields['author'].choices = [('', 'Anyone')] + [(a['author'], a['author']) for a in queries.history_authors(user.id)]

    def clean(self):
        cleaned = super().clean()
        (start, end) = (cleaned.get('date_from'), cleaned.get('date_to'))
        if start and end and (start > end):
            self.add_error('date_to', "'To' must be on or after 'From'.")
        return cleaned
