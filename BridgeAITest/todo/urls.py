from django.urls import path
from .views import (TodoAPIView, TodoListCreateView,
                    TodoListView, TodoCreateView,
                    TodoUpdateView, TodoDeleteView,
                    TodoDetailView, TodoDetailEditDeleteView)

urlpatterns = [
    path('basic/', TodoAPIView.as_view()),
    path('todos/', TodoListView.as_view()),
    path('todos/create/', TodoCreateView.as_view()),
    path('todos/<int:id>/', TodoDetailView.as_view()),
    path('todos/<int:id>/update/', TodoUpdateView.as_view()),
    path('todos/<int:id>/delete/', TodoDeleteView.as_view()),
    path('todos/list-create/', TodoListCreateView.as_view()),
    path('todos/<int:id>/crud/', TodoDetailEditDeleteView.as_view()),
]