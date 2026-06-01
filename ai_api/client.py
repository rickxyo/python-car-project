import logging
import os
from typing import Any


LOGGER = logging.getLogger(__name__)
DEFAULT_GEMINI_MODEL = 'gemini-2.5-flash-lite'
MAX_OUTPUT_TOKENS = 120


def _brand_name(brand: Any) -> str:
    return getattr(brand, 'name', str(brand))


def _env_bool(var_name: str, default: bool = False) -> bool:
    value = os.getenv(var_name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def get_car_ai_description(model, brand, year):
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        LOGGER.warning('GEMINI_API_KEY is not configured. Skipping car description generation.')
        return None

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        LOGGER.exception('google-genai package is not available. Skipping car description generation.')
        return None

    brand_text = _brand_name(brand)
    model_name = os.getenv('GEMINI_MODEL', DEFAULT_GEMINI_MODEL)
    trust_env = _env_bool('GEMINI_TRUST_ENV', default=False)
    prompt = (
        'Write a compelling car sales description in English with up to 250 characters. '
        'Include practical technical highlights for this exact model.\n'
        f'Car: {brand_text} {model} {year}.'
    )

    try:
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                client_args={'trust_env': trust_env},
            ),
        )
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=MAX_OUTPUT_TOKENS,
                temperature=0.4,
            ),
        )
    except Exception:
        LOGGER.exception(
            'Gemini request failed while generating description for %s %s %s.',
            brand_text,
            model,
            year,
        )
        return None

    text = (getattr(response, 'text', '') or '').strip()
    if not text:
        LOGGER.warning(
            'Gemini returned an empty description for %s %s %s.',
            brand_text,
            model,
            year,
        )
        return None

    return text
