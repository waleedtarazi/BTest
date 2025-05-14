from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import Todo
from .serializers import TodoSerializer
from django.views.generic.edit import CreateView
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from .mixins import TodoListMixin, TodoDetailMixin 
import json

#Django
# class based view:
class TodoView(TodoListMixin, TodoDetailMixin, View):
    def get(self, request, pk=None):
        if pk:
            todo = self.get_todo(pk)
            if todo:
                return JsonResponse({
                    "id" : todo.id,
                    "title": todo.title,
                    "completed": todo.completed
                },status=200)
            else:
                return JsonResponse({
                    "error": "todo couldn't be found"}, status=404)
        else:
            todos = list(self.get_todos().values())
            return JsonResponse(todos, safe=False)
        
    def post(self, request):
        data = json.loads(request.body)
        title = data.get('title')
        completed = data.get('completed')
        todo = Todo.objects.create(title="Some Title", completed=False)
        print(type(todo))
        return JsonResponse({
                    "id" : todo.id,
                    "title": todo.title,
                    "completed": todo.completed
                },status=201)
        
    def put(self,request, pk = None):
        if not pk:
            return JsonResponse({
                "error", "Missing ID ",
            }, status = 400)
        todo = self.get_todo(pk)
        if todo:
            data = json.load(request.body)
            todo.title = data.get('title', todo.title)
            todo.completed = data.get('completed', todo.completed)    
            todo.save()
            return JsonResponse({
                'message' : "Todo updated successfully",
            })
        return JsonResponse({
            'error': "Todo not found !"
        }, status= 404)
        
        
    def delete(self,request,pk=None):
        if not pk:
            return JsonResponse({
                "error", "Missing ID ",
                }, status = 400)
        todo = self.get_todo(pk)
        if todo:
            todo.delete()
            return JsonResponse({
                "message": "todo deleted successfully"
            })
            
        return JsonResponse({
            'error': "Todo not found !"
        }, status= 404)



#DRF
## Function based view:
@api_view(['GET'])
def get_all_todos(request):
    todos = Todo.objects.all()
    serializer = TodoSerializer(data = todos.data, many=True)
    return Response(serializer.data)

@api_view(['POST'])
def create_todo(request):
    serializer = TodoSerializer(data = request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    else:
        return Response(serializer.errors, status=400)

## API View(Class based view) ##
class TodoAPIView(APIView):
    def get(self, request):
        todos = Todo.objects.all()
        serializer = TodoSerializer(todos, many=True)
        return Response(serializer.data)
    
    def post(self,request):
        serialzer = TodoSerializer(data = request.data)
        if serialzer.is_valid():
            serialzer.save()
            return Response(serialzer.data, status=201)
        else:
            return Response(serialzer.errors, status=400)

