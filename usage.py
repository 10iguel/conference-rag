# Pricing per 1M tokens (USD) for current OpenAI models, including audio-capable models,
# from the official OpenAI pricing page.
import logging
import sys

from openai.types.responses import ResponseUsage

logger = logging.getLogger(__name__)

PRICING = {
    # Current general-purpose and reasoning models.
    'gpt-6-astra': {'input': 10.00, 'cached': 1.00, 'output': 50.00},
    'gpt-5.6-sol': {'input': 4.00, 'cached': 0.40, 'output': 20.00},
    'gpt-5.6-terra': {'input': 2.00, 'cached': 0.20, 'output': 12.00},
    'gpt-5.6-luna': {'input': 0.20, 'cached': 0.02, 'output': 1.20},
    'gpt-5.6-cyber': {'input': 12.50, 'cached': 1.25, 'output': 75.00},
    'gpt-daybreak-blue-latest': {'input': 4.00, 'cached': 0.40, 'output': 20.00},
    'gpt-daybreak-red-latest': {'input': 12.50, 'cached': 1.25, 'output': 75.00},
    'chat-latest': {'input': 5.00, 'cached': 0.50, 'output': 30.00},
    'gpt-5.4': {'input': 2.25, 'cached': 0.225, 'output': 18.00},
    'gpt-5.4-pro': {'input': 27.00, 'cached': 0.0, 'output': 216.00},
    'gpt-5.3-chat-latest': {'input': 1.75, 'cached': 0.175, 'output': 14.00},
    'gpt-5.3-codex': {'input': 1.75, 'cached': 0.175, 'output': 14.00},
    'gpt-5.2': {'input': 1.75, 'cached': 0.175, 'output': 14.00},
    'gpt-5.2-chat-latest': {'input': 1.75, 'cached': 0.175, 'output': 14.00},
    'gpt-5.2-codex': {'input': 1.75, 'cached': 0.175, 'output': 14.00},
    'gpt-5.2-pro': {'input': 21.00, 'cached': 0.0, 'output': 168.00},
    'gpt-5.1': {'input': 1.25, 'cached': 0.125, 'output': 10.00},
    'gpt-5.1-chat-latest': {'input': 1.25, 'cached': 0.125, 'output': 10.00},
    'gpt-5.1-codex': {'input': 1.25, 'cached': 0.125, 'output': 10.00},
    'gpt-5.1-codex-max': {'input': 1.25, 'cached': 0.125, 'output': 10.00},
    'gpt-5': {'input': 1.25, 'cached': 0.125, 'output': 10.00},
    'gpt-5-chat-latest': {'input': 1.25, 'cached': 0.125, 'output': 10.00},
    'gpt-5-codex': {'input': 1.25, 'cached': 0.125, 'output': 10.00},
    'gpt-5-pro': {'input': 15.00, 'cached': 0.0, 'output': 120.00},
    'gpt-5-mini': {'input': 0.25, 'cached': 0.025, 'output': 2.00},
    'gpt-5-nano': {'input': 0.05, 'cached': 0.005, 'output': 0.40},
    'gpt-4.1': {'input': 2.00, 'cached': 0.50, 'output': 8.00},
    'gpt-4.1-mini': {'input': 0.40, 'cached': 0.10, 'output': 1.60},
    'gpt-4.1-nano': {'input': 0.10, 'cached': 0.025, 'output': 0.40},
    'gpt-4o-transcribe': {'input': 0.0, 'cached': 0.0, 'output': 10.00, 'audio_input': 2.50},
    'gpt-4o-mini-transcribe': {'input': 0.0, 'cached': 0.0, 'output': 5.00, 'audio_input': 1.25},
    'gpt-4o-mini-tts': {'input': 0.60, 'cached': 0.0, 'output': 0.0, 'audio_output': 12.00},
    'gpt-4o-audio-preview': {
        'input': 2.50,
        'cached': 1.25,
        'output': 10.00,
        'audio_input': 40.00,
        'audio_output': 80.00,
    },
    'gpt-4o-mini-audio-preview': {
        'input': 0.15,
        'cached': 0.075,
        'output': 0.60,
        'audio_input': 10.00,
        'audio_output': 20.00,
    },
    'gpt-audio': {
        'input': 2.50,
        'cached': 1.25,
        'output': 10.00,
        'audio_input': 32.00,
        'audio_output': 64.00,
    },
    'gpt-audio-mini': {'input': 0.60, 'cached': 0.30, 'output': 2.40},
    'gpt-realtime-2.1': {
        'input': 4.00,
        'cached': 0.40,
        'output': 24.00,
        'audio_input': 32.00,
        'audio_output': 64.00,
    },
    'gpt-realtime-2.1-mini': {
        'input': 0.60,
        'cached': 0.06,
        'output': 2.40,
        'audio_input': 10.00,
        'audio_output': 20.00,
    },
    'gpt-image-2.5-sunburst': {'input': 5.00, 'cached': 1.25, 'output': 0.0},
    'gpt-image-2.5-flare': {'input': 5.00, 'cached': 1.25, 'output': 0.0},
    'whisper-1': {'input': 0.006, 'cached': 0.0, 'output': 0.0},
}


def _calculate_cost_usd(totals: dict[str, dict]) -> float:
    total = 0
    for model, usage in totals.items():
        rates = PRICING.get(model)
        if not rates:
            logger.warning('No pricing rates configured for model %s', model)
            continue

        audio_input = usage.get('audio_input', 0)
        audio_output = usage.get('audio_output', 0)
        text_input = max(usage['input'] - usage['cached'] - audio_input, 0)
        cached_input = usage['cached']
        text_output = max(usage['output'] - audio_output, 0)

        total += text_input * rates.get('input', 0.0)
        total += cached_input * rates.get('cached', rates.get('input', 0.0))
        total += text_output * rates.get('output', 0.0)
        total += audio_input * rates.get('audio_input', 0.0)
        total += audio_output * rates.get('audio_output', 0.0)
    # Prices are per 1M tokens.
    return total / 1_000_000


def _aggregate_usage(usages: list[tuple[str, ResponseUsage]]):
    total = {}
    for model, usage in usages:
        if model not in total:
            total[model] = {
                'input': 0,
                'cached': 0,
                'output': 0,
                'reasoning': 0,
                'audio_input': 0,
                'audio_output': 0,
            }
        total[model]['input'] += usage.input_tokens
        if hasattr(usage, 'input_tokens_details'):
            total[model]['cached'] += usage.input_tokens_details.cached_tokens
        if hasattr(usage, 'input_token_details'):
            total[model]['audio_input'] += getattr(usage.input_token_details, 'audio_tokens', 0)
        total[model]['output'] += usage.output_tokens
        if hasattr(usage, 'output_tokens_details'):
            total[model]['reasoning'] += usage.output_tokens_details.reasoning_tokens
        if hasattr(usage, 'output_token_details'):
            total[model]['audio_output'] += getattr(usage.output_token_details, 'audio_tokens', 0)
    return total


def print_usage(usages: list[tuple[str, ResponseUsage]], file=sys.stderr):
    print(' Usage '.center(30, '-'), file=file)
    totals = _aggregate_usage(usages)
    for model, total in totals.items():
        print(model.center(30, '~'), file=file)
        for key, value in total.items():
            if value:
                print(f'{key.title()} (tokens):', value, file=file)
        cost = _calculate_cost_usd({model: total})
        print(f'{model} cost (USD): ${cost:.6f}', file=file)

    cost = _calculate_cost_usd(totals)
    print('~'*30, file=file)
    print(f'Total cost (USD): ${cost:.6f}', file=file)


def format_usage_markdown(model: str, usages: list[ResponseUsage]) -> str:
    """Format single-model usage as Markdown for lecture UIs."""
    if not isinstance(usages, list):
        usages = [usages]
    totals = _aggregate_usage([(model, usage) for usage in usages])
    total = totals.get(model, {
        'input': 0,
        'cached': 0,
        'output': 0,
        'reasoning': 0,
        'audio_input': 0,
        'audio_output': 0,
    })
    cost = _calculate_cost_usd({model: total})
    token_table = '\n'.join(
        f"| {key.title()} | {value} |"
        for key, value in total.items()
        if value
    )
    return (
        "# Usage\n\n"
        f"**Model**: `{model}`\n\n"
        "|    | Tokens |\n"
        "|----|--------|\n"
        f"{token_table}\n\n"
        f"**Total cost**: ${cost:.6f}\n"
    )
