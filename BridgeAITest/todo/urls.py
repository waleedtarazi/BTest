from django.urls import path
from .views import (TodoListView, TodoDetailView,
                    TodoView, 
                    create_todo, get_all_todos,
                    update_todo, get_todo,
                    delete_todo)

# DRF: django rest framework
# CBV: class based view
# FBV: funstion based view
# allbasics: get,post,all,put,delete
#  
urlpatterns = [
    path('todos/django/CBV/allbasics/', TodoView.as_view()),
    path('todos/django/CBV/allbasics/<int:pk>/', TodoView.as_view()),
    
    path('todos/DRF/FBV/all/', get_all_todos),
    path('todos/DRF/FBV/<int:pk>/', get_todo),
    path('todos/DRF/FBV/create/', create_todo),
    path('todos/DRF/FBV/update/<int:pk>/',update_todo ),
    path('todos/DRF/FBV/delete/<int:pk>/',delete_todo ),

    path('todos/DRF/CBV/', TodoListView.as_view()),
    path('todos/DRF/CBV/<int:pk>/', TodoDetailView.as_view()),
]