from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import Todo
from .serializers import TodoSerializer
from django.http import JsonResponse
from django.views import View
from .mixins import TodoListMixin, TodoDetailMixin 
import json

#Django
# class based view:
class TodoView(TodoListMixin, TodoDetailMixin, View):
    def get(self, request, pk=None):
        if pk:
            todo = self.get_todo(pk)
            if todo:
                serializer = TodoSerializer(todo)
                return Response(serializer.data)
            else:
                return Response({
                    "error": "Todo couldn't be found"}, status=404)
        else:
            todos = get_all_todos()
            serializer = TodoSerializer(data = todos.data, many=True)
            return Response(serializer.data)
        
    def post(self, request):
        data = json.loads(request.body)
        serializer = TodoSerializer(data = data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data,status=201)
        return JsonResponse(serializer.errors, status= 400)
        
    def put(self,request, pk = None):
        if not pk:
            return Response({
                "error", "Missing ID ",
            }, status = 400)
        todo = self.get_todo(pk)
        if todo:
            data = json.loads(request.body)
            serializer = TodoSerializer(todo, data=data)
            if serializer.is_valid():
                return Response({
                    'message' : "Todo updated successfully",
                    'todo' : serializer.data,
                })
        return Response({
            'error': "Todo not found !"
        }, status= 404)
        
        
    def delete(self,request,pk=None):
        if not pk:
            return Response({
                "error", "Missing ID ",
                }, status = 400)
        todo = self.get_todo(pk)
        if todo:
            todo.delete()
            return Response({
                "message": "todo deleted successfully"
            })
            
        return Response({
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

