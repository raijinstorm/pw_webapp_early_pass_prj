from django import forms
from app.templatetags.app_extras import bootstrap, role_badge, show

def test_show_empty_and_booleans():
    assert '—' in show(None)
    assert '—' in show('')
    assert 'Yes' in show(True)
    assert 'No' in show(False)
    assert show(42) == 42

def test_role_badge():
    assert role_badge(None) == ''
    assert 'text-bg-primary' in role_badge('manager')
    assert 'Admin' in role_badge('admin')

class PlainForm(forms.Form):
    name = forms.CharField()
    agree = forms.BooleanField()
    kind = forms.ChoiceField(choices=[('a', 'A')])

def test_bootstrap_filter_adds_classes():
    form = PlainForm({'name': ''})
    form.is_valid()
    assert 'class="form-control is-invalid"' in bootstrap(form['name'])
    assert 'form-check-input' in bootstrap(form['agree'])
    assert 'form-select' in bootstrap(form['kind'])

def test_bootstrap_filter_keeps_existing_classes():
    form = PlainForm()
    form.fields['name'].widget.attrs['class'] = 'custom'
    assert bootstrap(form['name']) is form['name']
