import os
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class Settings(BaseModel):
    servicenow_base_url: str = os.getenv("SERVICENOW_BASE_URL", "")
    servicenow_username: str = os.getenv("SERVICENOW_USERNAME", "")
    servicenow_password: str = os.getenv("SERVICENOW_PASSWORD", "")
    confluence_base_url: str = os.getenv("CONFLUENCE_BASE_URL", "")
    confluence_username: str = os.getenv("CONFLUENCE_USERNAME", "")
    confluence_api_token: str = os.getenv("CONFLUENCE_API_TOKEN", "")
    confluence_space_key: str = os.getenv("CONFLUENCE_SPACE_KEY", "OPS")


settings = Settings()