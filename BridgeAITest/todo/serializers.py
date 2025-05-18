from rest_framework import serializers
from .models import Todo

class TodoSerializer(serializers.ModelSerializer):
    total_number_of_todos = serializers.SerializerMethodField()
    user_id = serializers.IntegerField(source='user.id', read_only=True)  # <-- Add this line

    
    class Meta:
        model = Todo
        fields = ['id', 'title', 'completed','user_id', 'total_number_of_todos']
        read_only_fields = ['user', 'created_at']
        
    def get_total_number_of_todos(self, todo):
        return Todo.objects.count()