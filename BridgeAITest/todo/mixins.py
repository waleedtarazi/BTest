from .models import Todo

class TodoListMixin:
    def get_todos(self):
        return Todo.objects.all()
    
class TodoDetailMixin:
    def get_todo(self,pk):
        try:
            todo =Todo.objects.get(pk = pk)
            return todo
            # DoesNotExist -> a predefinded attribute 
        except Todo.DoesNotExist:
            return None