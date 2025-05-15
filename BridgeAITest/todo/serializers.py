from rest_framework import serializers
from .models import Todo

class TodoSerializer(serializers.ModelSerializer):
    total_number_of_todos = serializers.SerializerMethodField()
    
    class Meta:
        model = Todo
        fields = ['id', 'title', 'completed', 'total_number_of_todos']
        
    def get_total_number_of_todos(self, todo):
        return Todo.objects.count()