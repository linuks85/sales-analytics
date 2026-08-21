"""Модуль анализа клиентов (контрагентов)."""

import pandas as pd
import plotly.graph_objects as go

_CHURN_THRESHOLD_DAYS = 30


def client_summary(df, client_col, amount_col, date_col):
    """Рассчитывает сводку по клиентам.

    Возвращает DataFrame с колонками:
        контрагент, сумма, количество_сделок, средний_чек,
        первая_покупка, последняя_покупка, дней_без_покупки
    (дней_без_покупки считается относительно последней даты в данных)
    """
    grouped = (
        df.groupby(client_col)
        .agg(
            сумма=(amount_col, "sum"),
            количество_сделок=(amount_col, "count"),
            первая_покупка=(date_col, "min"),
            последняя_покупка=(date_col, "max"),
        )
        .reset_index()
        .rename(columns={client_col: "контрагент"})
    )

    grouped["средний_чек"] = grouped["сумма"] / grouped["количество_сделок"]

    reference_date = df[date_col].max()
    grouped["дней_без_покупки"] = (reference_date - grouped["последняя_покупка"]).dt.days

    grouped = grouped[
        [
            "контрагент",
            "сумма",
            "количество_сделок",
            "средний_чек",
            "первая_покупка",
            "последняя_покупка",
            "дней_без_покупки",
        ]
    ]

    return grouped.sort_values("сумма", ascending=False).reset_index(drop=True)


def churn_risk(df):
    """Отбирает клиентов, не покупавших более 30 дней.

    Принимает DataFrame в формате, возвращаемом client_summary.
    Возвращает DataFrame с колонками:
        контрагент, последняя_покупка, дней_без_покупки, сумма_всего
    Отсортирован по дней_без_покупки (сначала самые долгие).
    """
    at_risk = df[df["дней_без_покупки"] > _CHURN_THRESHOLD_DAYS].copy()
    at_risk = at_risk.rename(columns={"сумма": "сумма_всего"})
    at_risk = at_risk[["контрагент", "последняя_покупка", "дней_без_покупки", "сумма_всего"]]

    return at_risk.sort_values("дней_без_покупки", ascending=False).reset_index(drop=True)


def plot_clients(df):
    """Строит горизонтальный bar chart топ-10 клиентов по выручке.

    Принимает DataFrame в формате, возвращаемом client_summary.
    """
    top10 = df.nlargest(10, "сумма").sort_values("сумма")

    fig = go.Figure(
        go.Bar(
            x=top10["сумма"],
            y=top10["контрагент"],
            orientation="h",
            marker_color="#3498db",
        )
    )
    fig.update_layout(
        title="Топ-10 клиентов по выручке",
        xaxis_title="Сумма, ₸",
        yaxis_title="Контрагент",
    )
    return fig


def get_clients_insights(df):
    """Формирует список текстовых выводов о клиентах на русском языке.

    Принимает DataFrame в формате, возвращаемом client_summary.
    """
    insights = []

    if df.empty:
        return insights

    top = df.loc[df["сумма"].idxmax()]
    insights.append(f"Топ клиент: {top['контрагент']} — {top['сумма']:,.0f} ₸")

    at_risk = churn_risk(df)
    if not at_risk.empty:
        insights.append(f"{len(at_risk)} клиентов не покупали более 30 дней — риск оттока")

    avg_check = df["средний_чек"].mean()
    insights.append(f"Средний чек по всем клиентам: {avg_check:,.0f} ₸")

    reference_date = df["последняя_покупка"].max()
    new_clients = df[df["первая_покупка"] > reference_date - pd.Timedelta(days=30)]
    insights.append(f"Новых клиентов за последний месяц: {len(new_clients)}")

    return insights
