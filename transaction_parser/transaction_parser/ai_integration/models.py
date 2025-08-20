from dataclasses import dataclass
from enum import Enum


class ResponseFormat(Enum):
    """Enumeration for AI model response formats."""

    JSON = "json_object"
    TEXT = "text"


@dataclass
class Model:
    """Base model configuration for AI services."""

    name: str
    service_provider: str
    base_url: str
    response_format: str


### DeepSeek Models


@dataclass
class DeepSeekChat(Model):
    """DeepSeek Chat model configuration."""

    name: str = "deepseek-chat"
    service_provider: str = "DeepSeek"
    base_url: str = "https://api.deepseek.com"
    response_format: str = ResponseFormat.JSON.value


@dataclass
class DeepSeekReasoner(Model):
    """DeepSeek Reasoner model configuration."""

    name: str = "deepseek-reasoner"
    service_provider: str = "DeepSeek"
    base_url: str = "https://api.deepseek.com"
    response_format: str = ResponseFormat.TEXT.value


### OpenAI Models


@dataclass
class OpenAIGPT4o(Model):
    """OpenAI GPT-4o model configuration."""

    name: str = "gpt-4o"
    service_provider: str = "OpenAI"
    base_url: str = "https://api.openai.com/v1"
    response_format: str = ResponseFormat.JSON.value


@dataclass
class OpenAIGPT4oMini(Model):
    """OpenAI GPT-4o Mini model configuration."""

    name: str = "gpt-4o-mini"
    service_provider: str = "OpenAI"
    base_url: str = "https://api.openai.com/v1"
    response_format: str = ResponseFormat.JSON.value


### Model Registry

MODELS = {
    "DeepSeek Chat": DeepSeekChat(),
    "DeepSeek Reasoner": DeepSeekReasoner(),
    "OpenAI gpt-4o": OpenAIGPT4o(),
    "OpenAI gpt-4o-mini": OpenAIGPT4oMini(),
}
