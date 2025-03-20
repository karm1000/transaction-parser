from enum import Enum


class ResponseFormat(Enum):
    JSON = "json_object"
    TEXT = "text"


class Model:
    name = None
    base_url = None
    response_format = None


class DeepSeek(Model):
    base_url = "https://api.deepseek.com"
    response_format = ResponseFormat.JSON.value


class DeepSeekChat(DeepSeek):
    name = "deepseek-chat"


class DeepSeekReasoner(DeepSeek):
    name = "deepseek-reasoner"
    response_format = ResponseFormat.TEXT.value


MODELS = {
    "DeepSeek Chat": DeepSeekChat,
    "DeepSeek Reasoner": DeepSeekReasoner,
}
