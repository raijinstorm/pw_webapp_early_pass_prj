from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField
from django.core.validators import RegexValidator
from django.db import models

class User(AbstractUser):

    class Meta:
        db_table = 'app_user'

class Role(models.TextChoices):
    MANAGER = ('manager', 'Manager')
    EDITOR = ('editor', 'Editor')

class Product(models.Model):
    code = models.CharField(max_length=50, unique=True, validators=[RegexValidator('^[a-z0-9]+(-[a-z0-9]+)*$', 'Lowercase letters, digits and single hyphens.')], help_text='Short identifier used in URLs, e.g. pricing-feed.')
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'product'
        ordering = ['name']

    def __str__(self):
        return self.name

class Client(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'client'
        ordering = ['name']

    def __str__(self):
        return self.name

class SchemaField(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='fields')
    key = models.CharField(max_length=50)
    label = models.CharField(max_length=100)
    field_type = models.CharField(max_length=20)
    required = models.BooleanField(default=True)
    min_value = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    max_value = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    choices = ArrayField(models.TextField(), null=True, blank=True)
    pattern = models.TextField(null=True, blank=True)
    help_text = models.TextField(blank=True, default='')
    position = models.IntegerField(default=0)

    class Meta:
        db_table = 'schema_field'

    def __str__(self):
        return f'{self.product.code}.{self.key}'

class Configuration(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, default='active')
    data = models.JSONField(default=dict)
    version = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, related_name='+')

    class Meta:
        db_table = 'configuration'

    def __str__(self):
        return f'{self.product} / {self.client}'
