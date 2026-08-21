"""Модуль анализа динамики продаж по месяцам."""

import pandas as pd
import plotly.graph_objects as go

_MONTHS_RU = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь",
}


def _format_month(timestamp):
    """Форматирует Timestamp начала месяца в вид «Декабрь 2024»."""
    return f"{_MONTHS_RU[timestamp.month]} {timestamp.year}"


def monthly_sales(df, date_col, amount_col):
    """Рассчитывает продажи по месяцам.

    Возвращает DataFrame с колонками:
        месяц (Timestamp, начало месяца), сумма, количество_сделок, рост_%
    (рост_% — изменение суммы по сравнению с предыдущим месяцем)
    """
    months = pd.Series(df[date_col].values.astype("datetime64[M]"), name="месяц")
    grouped = (
        df[amount_col]
        .groupby(months)
        .agg(сумма="sum", количество_сделок="count")
        .reset_index()
        .sort_values("месяц")
        .reset_index(drop=True)
    )
    grouped["рост_%"] = grouped["сумма"].pct_change().mul(100).round(2)

    return grouped


def best_worst_months(df):
    """Определяет лучший и худший месяц по сумме продаж.

    Принимает DataFrame в формате, возвращаемом monthly_sales.
    Возвращает словарь:
        {"лучший_месяц": "Декабрь 2024", "сумма": 5200000,
         "худший_месяц": "Июль 2024", "сумма_худшего": 1200000}
    """
    if df.empty:
        return {}

    best = df.loc[df["сумма"].idxmax()]
    worst = df.loc[df["сумма"].idxmin()]

    return {
        "лучший_месяц": _format_month(pd.Timestamp(best["месяц"])),
        "сумма": best["сумма"],
        "худший_месяц": _format_month(pd.Timestamp(worst["месяц"])),
        "сумма_худшего": worst["сумма"],
    }


def plot_dynamics(df):
    """Строит столбчатый график продаж по месяцам.

    Принимает DataFrame в формате, возвращаемом monthly_sales.
    Столбцы окрашены зелёным при росте и красным при падении,
    над каждым столбцом подписан % роста/падения.
    """
    labels = [_format_month(pd.Timestamp(m)) for m in df["месяц"]]
    colors = ["#e74c3c" if v < 0 else "#2ecc71" for v in df["рост_%"].fillna(0)]
    text = [f"{v:+.1f}%" if pd.notna(v) else "" for v in df["рост_%"]]

    fig = go.Figure(
        go.Bar(
            x=labels,
            y=df["сумма"],
            marker_color=colors,
            text=text,
            textposition="outside",
        )
    )
    fig.update_layout(
        title="Динамика продаж по месяцам",
        xaxis_title="Месяц",
        yaxis_title="Сумма, ₸",
        showlegend=False,
    )
    return fig


def get_dynamics_insights(df):
    """Формирует список текстовых выводов о динамике продаж на русском языке."""
    insights = []

    if df.empty:
        return insights

    summary = best_worst_months(df)
    insights.append(f"{summary['лучший_месяц']} — лучший месяц: {summary['сумма']:,.0f} ₸")
    insights.append(f"{summary['худший_месяц']} — худший месяц: {summary['сумма_худшего']:,.0f} ₸")

    growth = df["рост_%"].dropna()
    if not growth.empty:
        avg_growth = growth.mean()
        insights.append(f"Средний месячный рост: {avg_growth:+.0f}%")

    last_growth = df["рост_%"].tail(3).dropna()
    if len(last_growth) == 3:
        if (last_growth > 0).all():
            insights.append("Последние 3 месяца: устойчивый рост")
        elif (last_growth < 0).all():
            insights.append("Последние 3 месяца: устойчивое падение")

    return insights
