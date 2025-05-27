from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import ChatSession, ChatMessage, LLMProvider
from .serializers import ChatRequestSerializer, ChatResponseSerializer
from .services.langchain_service import get_llm_from_provider, TokenUsageCallback, create_agent, fall_back_chat
from langchain_core.exceptions import OutputParserException
from langchain.schema import HumanMessage

class ChatAPIView(APIView):
    def post(self, request):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Retrieve or create chat session
        session_id = data.get("session_id")
        if session_id:
            session = ChatSession.objects.get(id=session_id)
        else:
            session = ChatSession.objects.create()

        user_message = data["message"]
        # Log user message
        ChatMessage.objects.create(
            session=session, role="user", content=user_message
        )
        

        # Prepare LangChain model and tools
        provider = LLMProvider.objects.get(is_active=True)
        llm = get_llm_from_provider(provider)
        agent = create_agent(llm)
        callback = TokenUsageCallback()
        print(f"--- Testing LLM directly ---")
        print(f"User message for LLM: '{user_message}'")
        try:
            result = agent.invoke(user_message,config=[callback])
            print("\n\nresult: " + result + '\n\n')
        except OutputParserException as ope:
            fallback_chat = fall_back_chat(provider)
        # use .invoke for the new API, or __call__ if you haven't upgraded
            result = fallback_chat.invoke(
            input=[HumanMessage(content=user_message)]
            )

        print(f"LLM direct response type: {type(result)}")
        print(f"LLM direct response content: '{result}'")
        print(f"--- LLM direct test complete ---")
        if isinstance(result, dict):
            reply = result['output']
        elif isinstance(result, str):
            reply = result
        # reply = result

        # Log assistant response with usage
        ChatMessage.objects.create(
            session=session,
            role="assistant",
            content=reply,
            tokens_prompt=callback.prompt_tokens,
            tokens_completion=callback.completion_tokens,
            tokens_total=callback.total_tokens,
            cost=callback.cost
        )

        # Prepare response
        output = {
            "session_id": session.id,
            "response": result,
            "tokens_prompt": callback.prompt_tokens,
            "tokens_completion": callback.completion_tokens,
            "tokens_total": callback.total_tokens,
            "cost": callback.cost
        }
        out_serializer = ChatResponseSerializer(output)
        return Response(out_serializer.data, status=status.HTTP_200_OK)
