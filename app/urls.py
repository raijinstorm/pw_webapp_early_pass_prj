from django.urls import path
from . import views
urlpatterns = [path('', views.dashboard, name='dashboard'), path('configs/<int:pk>/', views.config_detail, name='config_detail'), path('configs/<int:pk>/edit/', views.config_edit, name='config_edit'), path('products/<slug:code>/', views.product_detail, name='product_detail'), path('products/<slug:code>/configs/new/', views.config_create, name='config_create')]
