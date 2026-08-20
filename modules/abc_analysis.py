"""Модуль ABC-анализа продаж.

ABC-анализ ранжирует товары/контрагентов по выручке и делит их
на три категории по накопленной доле:
    A — первые 80% выручки (ключевые позиции)
    B — следующие 15%
    C — оставшиеся 5% (наименее значимые)
"""

import pandas as pd
import plotly.express as px

_COLORS = {"A": "#2ecc71", "B": "#f1c40f", "C": "#e74c3c"}


def _classify(cum_share):
    if cum_share <= 80:
        return "A"
    if cum_share <= 95:
        return "B"
    return "C"


def _analyze(df, group_col, amount_col):
    """Общая логика ABC-анализа по указанной группирующей колонке."""
    grouped = (
        df.groupby(group_col)[amount_col]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    grouped.columns = [group_col, "сумма"]

    total = grouped["сумма"].sum()
    grouped["доля_%"] = (grouped["сумма"] / total * 100).round(2)
    grouped["накопленная_%"] = grouped["доля_%"].cumsum().round(2)
    grouped["категория"] = grouped["накопленная_%"].apply(_classify)

    return grouped


def analyze_products(df, product_col, amount_col):
    """Рассчитывает ABC-категории товаров по выручке.

    Возвращает DataFrame с колонками:
        товар, сумма, доля_%, накопленная_%, категория
    """
    result = _analyze(df, product_col, amount_col)
    result = result.rename(columns={product_col: "товар"})
    return result[["товар", "сумма", "доля_%", "накопленная_%", "категория"]]


def analyze_clients(df, client_col, amount_col):
    """Рассчитывает ABC-категории контрагентов по выручке.

    Возвращает DataFrame с колонками:
        контрагент, сумма, доля_%, накопленная_%, категория
    """
    result = _analyze(df, client_col, amount_col)
    result = result.rename(columns={client_col: "контрагент"})
    return result[["контрагент", "сумма", "доля_%", "накопленная_%", "категория"]]


def plot_abc(df, title="ABC-анализ"):
    """Строит столбчатую диаграмму ABC-анализа с цветовой разбивкой по категориям."""
    name_col = df.columns[0]

    fig = px.bar(
        df,
        x=name_col,
        y="сумма",
        color="категория",
        color_discrete_map=_COLORS,
        category_orders={"категория": ["A", "B", "C"]},
        title=title,
        labels={name_col: name_col.capitalize(), "сумма": "Сумма, ₸"},
    )
    fig.update_layout(xaxis_tickangle=-45, showlegend=True)
    return fig


def get_abc_insights(df):
    """Формирует список текстовых выводов по результатам ABC-анализа на русском языке."""
    name_col = df.columns[0]
    insights = []

    for category, label in (("A", "категория A"), ("B", "категория B"), ("C", "категория C")):
        subset = df[df["категория"] == category]
        if subset.empty:
            continue
        share = subset["доля_%"].sum().round(1)
        insights.append(
            f"{label}: {len(subset)} из {len(df)} позиций дают {share}% выручки."
        )

    if not df.empty:
        top = df.iloc[0]
        insights.append(
            f"«{top[name_col]}» приносит {top['доля_%']}% выручки (категория {top['категория']})."
        )

    category_a = df[df["категория"] == "A"]
    if not category_a.empty and len(df) > 0:
        share_positions = round(len(category_a) / len(df) * 100, 1)
        insights.append(
            f"Всего {share_positions}% позиций формируют 80% выручки — "
            "именно на них стоит сфокусировать внимание."
        )

    category_c = df[df["категория"] == "C"]
    if not category_c.empty:
        insights.append(
            f"{len(category_c)} позиций в категории C приносят минимальный вклад в выручку "
            "— стоит пересмотреть их ассортимент или условия работы."
        )

    return insights
