from django.urls import path
from myapp import views

urlpatterns = [
    path('', views.index, name='index'), 
    path('form/', views.form, name='form'), 
    path('edit/<int:person_id>/', views.edit, name='edit'),     # เส้นทางแก้ไขข้อมูล
    path('delete/<int:person_id>/', views.delete, name='delete'), # เส้นทางลบข้อมูล
]