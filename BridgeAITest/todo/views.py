from rest_framework.generics import(
    ListAPIView, ListCreateAPIView,
    CreateAPIView, RetrieveAPIView,
    UpdateAPIView, DestroyAPIView,
    RetrieveUpdateDestroyAPIView
)
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Todo
from .serializers import TodoSerializer

## API View
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
        
# Generic Views
class TodoListView(ListAPIView):
    queryset = Todo.objects.all()
    serializer_class = TodoSerializer

class TodoCreateView(CreateAPIView):
    queryset = Todo.objects.all()
    serializer_class = TodoSerializer

class TodoDetailView(RetrieveAPIView):
    queryset = Todo.objects.all()
    serializer_class = TodoSerializer
    lookup_field = 'id'

class TodoUpdateView(UpdateAPIView):
    queryset = Todo.objects.all()
    serializer_class = TodoSerializer
    lookup_field = 'id'

class TodoDeleteView(DestroyAPIView):
    queryset = Todo.objects.all()
    serializer_class = TodoSerializer
    lookup_field = 'id'

class TodoListCreateView(ListCreateAPIView):
    queryset = Todo.objects.all()
    serializer_class = TodoSerializer

class TodoDetailEditDeleteView(RetrieveUpdateDestroyAPIView):
    queryset = Todo.objects.all()
    serializer_class = TodoSerializer
    lookup_field = 'id'
    
