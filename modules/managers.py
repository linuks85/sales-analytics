"""Модуль анализа эффективности менеджеров по продажам."""

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


def manager_summary(df, manager_col, amount_col, date_col):
    """Рассчитывает сводку по менеджерам.

    Возвращает DataFrame с колонками:
        менеджер, сумма, количество_сделок, средний_чек, доля_%
    (доля_% — доля менеджера от общей выручки по всем менеджерам)
    """
    grouped = (
        df.groupby(manager_col)
        .agg(
            сумма=(amount_col, "sum"),
            количество_сделок=(amount_col, "count"),
        )
        .reset_index()
        .rename(columns={manager_col: "менеджер"})
    )

    grouped["средний_чек"] = grouped["сумма"] / grouped["количество_сделок"]

    total = grouped["сумма"].sum()
    grouped["доля_%"] = (grouped["сумма"] / total * 100).round(2) if total else 0

    grouped = grouped[["менеджер", "сумма", "количество_сделок", "средний_чек", "доля_%"]]

    return grouped.sort_values("сумма", ascending=False).reset_index(drop=True)


def manager_monthly(df, manager_col, amount_col, date_col):
    """Рассчитывает продажи каждого менеджера по месяцам.

    Возвращает DataFrame с колонками:
        менеджер, месяц (Timestamp, начало месяца), сумма
    """
    months = pd.Series(df[date_col].values.astype("datetime64[M]"), index=df.index, name="месяц")

    grouped = (
        df.groupby([manager_col, months])[amount_col]
        .sum()
        .reset_index()
        .rename(columns={manager_col: "менеджер", amount_col: "сумма"})
        .sort_values(["менеджер", "месяц"])
        .reset_index(drop=True)
    )

    return grouped


def plot_managers(df):
    """Строит круговую диаграмму доли каждого менеджера в выручке.

    Принимает DataFrame в формате, возвращаемом manager_summary.
    """
    fig = go.Figure(
        go.Pie(
            labels=df["менеджер"],
            values=df["сумма"],
            hole=0.4,
        )
    )
    fig.update_layout(title="Доля менеджеров в выручке")
    return fig


def plot_managers_trend(df):
    """Строит линейный график продаж по месяцам для каждого менеджера.

    Принимает DataFrame в формате, возвращаемом manager_monthly.
    Каждый менеджер отображается отдельной линией своего цвета.
    """
    all_months = sorted(df["месяц"].unique())
    labels_order = [_format_month(pd.Timestamp(m)) for m in all_months]
    month_to_label = dict(zip(all_months, labels_order))

    fig = go.Figure()
    for manager, group in df.groupby("менеджер"):
        group = group.sort_values("месяц")
        fig.add_trace(
            go.Scatter(
                x=[month_to_label[m] for m in group["месяц"]],
                y=group["сумма"],
                mode="lines+markers",
                name=manager,
            )
        )

    fig.update_layout(
        title="Динамика продаж по менеджерам",
        xaxis_title="Месяц",
        yaxis_title="Сумма, ₸",
        xaxis=dict(categoryorder="array", categoryarray=labels_order),
    )
    return fig


def get_managers_insights(summary, monthly):
    """Формирует список текстовых выводов о менеджерах на русском языке.

    Принимает summary в формате manager_summary и monthly в формате manager_monthly.
    """
    insights = []

    if summary.empty:
        return insights

    top = summary.loc[summary["сумма"].idxmax()]
    insights.append(
        f"Лучший менеджер: {top['менеджер']} — {top['сумма']:,.0f} ₸ ({top['доля_%']:.0f}% выручки)"
    )

    avg_check_team = summary["средний_чек"].mean()
    if avg_check_team:
        ratio = top["средний_чек"] / avg_check_team
        if ratio >= 1.1:
            insights.append(f"Средний чек лидера в {ratio:.1f} раза выше среднего по команде")
        elif ratio <= 0.9:
            insights.append(f"Средний чек лидера в {1 / ratio:.1f} раза ниже среднего по команде")

    if not monthly.empty:
        growth = monthly.copy()
        growth["рост_%"] = growth.groupby("менеджер")["сумма"].pct_change().mul(100)

        for manager, group in growth.groupby("менеджер"):
            last3 = group["рост_%"].tail(3).dropna()
            if len(last3) == 3 and (last3 > 0).all():
                insights.append(
                    f"Менеджер {manager} показывает рост +{last3.mean():.0f}% последние 3 месяца"
                )
            elif len(last3) == 3 and (last3 < 0).all():
                insights.append(
                    f"Менеджер {manager} показывает падение {last3.mean():.0f}% последние 3 месяца"
                )

    return insights
