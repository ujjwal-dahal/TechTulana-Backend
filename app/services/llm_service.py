from langchain.chat_models import init_chat_model

#project imports
from app.core.config import settings

llm_1 = init_chat_model(
    model=settings.MODEL_NAME_1,
    model_provider=settings.MODEL_PROVIDER_1,
    api_key=settings.MODEL_API_KEY_1,
    temperature=0,
)

llm_2 = init_chat_model(
    model=settings.MODEL_NAME_2,
    model_provider=settings.MODEL_PROVIDER_2,
    api_key=settings.MODEL_API_KEY_2,
    temperature=0,
)



