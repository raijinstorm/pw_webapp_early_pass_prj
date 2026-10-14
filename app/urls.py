from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("configs/", views.config_list, name="config_list"),
    path("configs/<int:pk>/", views.config_detail, name="config_detail"),
    path("configs/<int:pk>/edit/", views.config_edit, name="config_edit"),
    path("configs/<int:pk>/status/", views.config_toggle_status, name="config_toggle_status"),
    path("versions/<int:pk>/", views.version_detail, name="version_detail"),
    path("versions/<int:pk>/restore/", views.version_restore, name="version_restore"),
    path("history/", views.history_list, name="history_list"),
    path("products/<slug:code>/", views.product_detail, name="product_detail"),
    path("products/<slug:code>/configs/new/", views.config_create, name="config_create"),
    path("products/<slug:code>/fields/new/", views.field_form, name="field_create"),
    path("products/<slug:code>/fields/<int:pk>/edit/", views.field_form, name="field_edit"),
    path("products/<slug:code>/fields/<int:pk>/delete/", views.field_delete, name="field_delete"),
    path("products/<slug:code>/members/add/", views.member_add, name="member_add"),
    path("members/<int:pk>/remove/", views.member_remove, name="member_remove"),
]
