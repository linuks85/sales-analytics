"""Модуль AI-советника.

Берёт текстовые выводы (insights) из модулей ABC-анализа и кассовых
разрывов, формирует из них промпт и запрашивает у Claude конкретные
бизнес-советы на русском языке.
"""

import anthropic

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 2000

_PROMPT_TEMPLATE = """Ты бизнес-аналитик для малого бизнеса Казахстана.
На основе данных дай 3-5 конкретных совета.
Данные по товарам: {abc_insights}
Данные по оплатам: {cashflow_insights}
Советы должны быть конкретными с цифрами в тенге."""


def get_advice(abc_insights, cashflow_insights, api_key):
    """Запрашивает у Claude бизнес-советы на основе insights.

    abc_insights и cashflow_insights — списки текстовых выводов
    (результат get_abc_insights / get_cashflow_insights).
    Возвращает текст советов или сообщение об ошибке на русском языке.
    """
    prompt = _PROMPT_TEMPLATE.format(
        abc_insights="; ".join(abc_insights),
        cashflow_insights="; ".join(cashflow_insights),
    )

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=_MODEL,
            max_tokens=_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        return next(block.text for block in response.content if block.type == "text")
    except anthropic.AuthenticationError:
        return "Ошибка: неверный API-ключ Claude. Проверьте ключ в настройках."
    except anthropic.PermissionDeniedError:
        return "Ошибка: у API-ключа недостаточно прав для выполнения запроса."
    except anthropic.RateLimitError:
        return "Ошибка: превышен лимит запросов к Claude API. Попробуйте позже."
    except anthropic.APIConnectionError:
        return "Ошибка: не удалось подключиться к Claude API. Проверьте интернет-соединение."
    except anthropic.APIStatusError as e:
        return f"Ошибка Claude API: {e.message}"
