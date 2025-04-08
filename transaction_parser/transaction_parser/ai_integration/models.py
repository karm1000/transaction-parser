from enum import Enum


class ResponseFormat(Enum):
    JSON = "json_object"
    TEXT = "text"


class Model:
    name = None
    service_provider = None
    base_url = None
    response_format = None


### deepseek


class DeepSeek(Model):
    service_provider = "DeepSeek"
    base_url = "https://api.deepseek.com"
    response_format = ResponseFormat.JSON.value


class DeepSeekChat(DeepSeek):
    name = "deepseek-chat"


class DeepSeekReasoner(DeepSeek):
    name = "deepseek-reasoner"
    response_format = ResponseFormat.TEXT.value


### openai


class OpenAI(Model):
    service_provider = "OpenAI"
    base_url = "https://api.openai.com/v1"
    response_format = ResponseFormat.JSON.value


class OpenAIGPT4o(OpenAI):
    name = "gpt-4o"


class OpenAIGPT4oMini(OpenAI):
    name = "gpt-4o-mini"


### model-class mapping

MODELS = {
    "DeepSeek Chat": DeepSeekChat,
    "DeepSeek Reasoner": DeepSeekReasoner,
    "OpenAI gpt-4o": OpenAIGPT4o,
    "OpenAI gpt-4o-mini": OpenAIGPT4oMini,
}
