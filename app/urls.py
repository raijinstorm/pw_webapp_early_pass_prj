from django.urls import path
from . import views
urlpatterns = [path('', views.dashboard, name='dashboard'), path('configs/<int:pk>/', views.config_detail, name='config_detail'), path('products/<slug:code>/', views.product_detail, name='product_detail')]
