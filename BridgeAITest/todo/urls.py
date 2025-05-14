from django.urls import path
from .views import (TodoAPIView, TodoView, 
                    create_todo, get_all_todos)

# DRF: django rest framework
# CBV: class based view
# FBV: funstion based view
# allbasics: get,post,all,put,delete
#  
urlpatterns = [
    path('todo/django/CBV/allbasics/', TodoView.as_view()),
    path('todo/django/CBV/allbasics/<int:pk>/', TodoView.as_view()),
    path('todos/DRF/FBV/all/', get_all_todos),
    path('todos/DRF/FBV/create/', create_todo),
    path('todo/DRF/CBV/basic/', TodoAPIView.as_view()),
]