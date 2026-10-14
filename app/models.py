"""ORM mirror of the database.

Only `User` is created by Django. The domain tables are created by the SQL files in sql/ (applied by
migration 0001), and all business rules live there: constraints, triggers and functions.

The domain models below contain no logic. They exist so that Django's admin can manage reference data
(products, clients, members) and so test tooling knows the tables. Pages query the database through
app/queries.py.
"""

from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import ArrayField
from django.core.validators import RegexValidator
from django.db import models


class User(AbstractUser):
    class Meta:
        db_table = "app_user"


class Role(models.TextChoices):
    MANAGER = "manager", "Manager"
    EDITOR = "editor", "Editor"


class Product(models.Model):
    code = models.CharField(
        max_length=50,
        unique=True,
        validators=[RegexValidator(r"^[a-z0-9]+(-[a-z0-9]+)*$", "Lowercase letters, digits and single hyphens.")],
        help_text="Short identifier used in URLs, e.g. pricing-feed.",
    )
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "product"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Client(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "client"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Membership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="memberships")
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EDITOR)

    class Meta:
        db_table = "membership"
        constraints = [models.UniqueConstraint(fields=["user", "product"], name="membership_unique")]

    def __str__(self):
        return f"{self.user} – {self.product} ({self.get_role_display()})"


class SchemaField(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="fields")
    key = models.CharField(max_length=50)
    label = models.CharField(max_length=100)
    field_type = models.CharField(max_length=20)
    required = models.BooleanField(default=True)
    min_value = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    max_value = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    choices = ArrayField(models.TextField(), null=True, blank=True)
    pattern = models.TextField(null=True, blank=True)
    help_text = models.TextField(blank=True, default="")
    position = models.IntegerField(default=0)

    class Meta:
        db_table = "schema_field"

    def __str__(self):
        return f"{self.product.code}.{self.key}"


class Configuration(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, default="active")
    data = models.JSONField(default=dict)
    version = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, related_name="+")

    class Meta:
        db_table = "configuration"

    def __str__(self):
        return f"{self.product} / {self.client}"


class ConfigVersion(models.Model):
    configuration = models.ForeignKey(Configuration, on_delete=models.PROTECT)
    number = models.IntegerField()
    data = models.JSONField()
    comment = models.TextField()
    author = models.ForeignKey(User, on_delete=models.PROTECT, null=True, related_name="+")
    created_at = models.DateTimeField()

    class Meta:
        db_table = "config_version"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.configuration} v{self.number}"
