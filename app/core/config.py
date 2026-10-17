
from dotenv import load_dotenv
import os 
load_dotenv()


class Settings:
  EXTRACTOR_API_URL = os.getenv("EXTRACTOR_API_URL")
  
  #model1
  MODEL_NAME_1 = os.getenv("MODEL_NAME_1")
  MODEL_API_KEY_1 = os.getenv("MODEL_API_KEY_1")
  MODEL_PROVIDER_1 = os.getenv("MODEL_PROVIDER_1")
  
  #model2
  MODEL_NAME_2 = os.getenv("MODEL_NAME_2")
  MODEL_API_KEY_2 = os.getenv("MODEL_API_KEY_2")
  MODEL_PROVIDER_2 = os.getenv("MODEL_PROVIDER_2")
  
  
  TAVILY_API_KEY=os.getenv("TAVILY_API_KEY")
  
  FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
  
  
settings = Settings()