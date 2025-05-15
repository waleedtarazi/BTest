from rest_framework.views import APIView
from rest_framework import generics
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
                return JsonResponse(serializer.data, safe=False)
            return JsonResponse({
                "error": "Todo couldn't be found"}, status=404)
        todos = self.get_todos()
        serializer = TodoSerializer(instance = todos, many=True)
        return JsonResponse(serializer.data, safe=False)
        
    def post(self, request):
        data = json.loads(request.body)
        serializer = TodoSerializer(data = data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data,status=201)
        return JsonResponse(serializer.errors, status= 400)
        
    def put(self,request, pk = None):
        if not pk:
            return JsonResponse({
                "error", "Missing ID ",
            }, status = 400)
        todo = self.get_todo(pk)
        if todo:
            data = json.loads(request.body)
            serializer = TodoSerializer(todo, data=data)
            if serializer.is_valid():
                serializer.save()
                return JsonResponse({
                    'message' : "Todo updated successfully",
                    'todo' : serializer.data,
                })
        return JsonResponse({
            'error': "Todo not found !"
        }, status= 404)
        
        
    def delete(self,request,pk=None):
        if not pk:
            return JsonResponse({
                "error": "Missing ID ",
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
    serializer = TodoSerializer(instance = todos, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def get_todo(request, pk):
    try:
        todo = Todo.objects.get(pk=pk)
    except Todo.DoesNotExist:
        return Response({'error': 'Todo not found'}, status=404)
    serializer = TodoSerializer(instance=todo)
    return Response(serializer.data)

@api_view(['POST'])
def create_todo(request):
    serializer = TodoSerializer(data = request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    else:
        return Response(serializer.errors, status=400)
    

@api_view(['PUT'])
def update_todo(request, pk):
    try:
        todo = Todo.objects.get(pk=pk)
    except:
        return Response({'error': 'Todo not found'}, status=404)
    update_serializer = TodoSerializer(todo, request.data)
    if update_serializer.is_valid():
        update_serializer.save()
        return Response({'message': 'todo updated',
                         'todo': update_serializer.data})
    return Response({'error':update_serializer.errors}, status=400)    

@api_view(['DELETE'])
def delete_todo(request,pk):
    try:
        todo = Todo.objects.get(pk=pk)
    except:
        return Response({'error': 'todo not found'}, status=404)
    todo.delete()
    return Response({'message': 'todo deleted '})
    

## API View(Class based view, Mixins) ##
class TodoListView(generics.ListCreateAPIView):
    queryset = Todo.objects.all()
    serializer_class = TodoSerializer

class TodoDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Todo.objects.all()
    serializer_class = TodoSerializer

