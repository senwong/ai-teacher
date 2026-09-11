import os


def provider_name() -> str:
    return os.getenv("AI_PROVIDER", "openai").strip().lower()


def api_key() -> str | None:
    key = os.getenv("AI_API_KEY")
    if key:
        return key
    if provider_name() == "deepseek":
        return os.getenv("DEEPSEEK_API_KEY")
    return os.getenv("OPENAI_API_KEY")


def base_url() -> str | None:
    value = os.getenv("AI_BASE_URL")
    if value:
        return value.rstrip("/")
    if provider_name() == "deepseek":
        return os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    return os.getenv("OPENAI_BASE_URL")


def text_model() -> str:
    model = os.getenv("AI_MODEL")
    if model:
        return model
    if provider_name() == "deepseek":
        return os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    return os.getenv("OPENAI_MODEL", "gpt-5.6-luna")


def vision_model() -> str:
    model = os.getenv("AI_VISION_MODEL")
    if model:
        return model
    if provider_name() == "deepseek":
        return os.getenv("DEEPSEEK_VISION_MODEL", "deepseek-v4-flash-vision-exp")
    return os.getenv("OPENAI_VISION_MODEL", text_model())


def enabled() -> bool:
    return bool(api_key())


def client():
    key = api_key()
    if not key:
        raise RuntimeError("AI_API_KEY is not configured")

    from openai import OpenAI

    kwargs = {"api_key": key}
    url = base_url()
    if url:
        kwargs["base_url"] = url
    return OpenAI(**kwargs)
