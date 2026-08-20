"""Модуль анализа кассовых разрывов.

Кассовый разрыв возникает, когда продажа уже состоялась, а оплата
за неё ещё не поступила: за период сумма продаж превышает сумму
фактически полученных оплат.
"""

import pandas as pd
import plotly.graph_objects as go

_MONTHS_RU = {
    1: "январе",
    2: "феврале",
    3: "марте",
    4: "апреле",
    5: "мае",
    6: "июне",
    7: "июле",
    8: "августе",
    9: "сентябре",
    10: "октябре",
    11: "ноябре",
    12: "декабре",
}


def calculate_gap(df, date_col, payment_col, amount_col):
    """Рассчитывает кассовый разрыв по дням.

    Возвращает DataFrame с колонками:
        дата, сумма_продаж, сумма_оплат, разрыв
    (разрыв = сумма_продаж - сумма_оплат за каждый день)
    """
    sales = df.groupby(df[date_col].dt.normalize())[amount_col].sum()
    paid = df.dropna(subset=[payment_col])
    payments = paid.groupby(paid[payment_col].dt.normalize())[amount_col].sum()

    result = pd.DataFrame({"сумма_продаж": sales, "сумма_оплат": payments}).fillna(0)
    result.index.name = "дата"
    result = result.reset_index().sort_values("дата").reset_index(drop=True)
    result["разрыв"] = result["сумма_продаж"] - result["сумма_оплат"]

    return result


def get_unpaid(df, date_col, payment_col, amount_col):
    """Возвращает неоплаченные строки (дата оплаты пустая), отсортированные по дате продажи."""
    unpaid = df[df[payment_col].isna()].copy()
    return unpaid.sort_values(date_col).reset_index(drop=True)


def plot_cashflow(df):
    """Строит линейный график продаж и оплат по месяцам.

    Принимает DataFrame в формате, возвращаемом calculate_gap
    (колонки: дата, сумма_продаж, сумма_оплат, разрыв).
    Месяцы, в которых образовался разрыв (продажи превысили оплаты),
    выделяются красной зоной.
    """
    monthly = (
        df.assign(месяц=df["дата"].values.astype("datetime64[M]"))
        .groupby("месяц")[["сумма_продаж", "сумма_оплат"]]
        .sum()
        .reset_index()
    )
    monthly["разрыв"] = monthly["сумма_продаж"] - monthly["сумма_оплат"]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=monthly["месяц"],
            y=monthly["сумма_продаж"],
            name="Продажи",
            mode="lines+markers",
            line=dict(color="#2ecc71"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=monthly["месяц"],
            y=monthly["сумма_оплат"],
            name="Оплаты",
            mode="lines+markers",
            line=dict(color="#3498db"),
        )
    )

    for _, row in monthly[monthly["разрыв"] > 0].iterrows():
        month_start = row["месяц"]
        month_end = month_start + pd.offsets.MonthBegin(1)
        fig.add_vrect(x0=month_start, x1=month_end, fillcolor="#e74c3c", opacity=0.15, line_width=0)

    fig.update_layout(
        title="Денежный поток: продажи vs оплаты",
        xaxis_title="Месяц",
        yaxis_title="Сумма, ₸",
        hovermode="x unified",
    )
    return fig


def get_cashflow_insights(df, date_col, payment_col, amount_col):
    """Формирует список текстовых выводов о кассовых разрывах на русском языке."""
    insights = []

    gap_df = calculate_gap(df, date_col, payment_col, amount_col)
    unpaid = get_unpaid(df, date_col, payment_col, amount_col)

    total_debt = gap_df["разрыв"].sum()
    insights.append(f"Текущий долг покупателей: {total_debt:,.0f} ₸")

    paid = df.dropna(subset=[payment_col, date_col])
    payment_days = (paid[payment_col] - paid[date_col]).dt.days
    payment_days = payment_days[payment_days >= 0]
    if not payment_days.empty:
        insights.append(f"Средний срок оплаты: {round(payment_days.mean())} дней")

    if not gap_df.empty:
        monthly_gap = gap_df.groupby(gap_df["дата"].values.astype("datetime64[M]"))["разрыв"].sum()
        worst_value = monthly_gap.max()
        if worst_value > 0:
            worst_month = pd.Timestamp(monthly_gap.idxmax())
            insights.append(
                f"Самый большой разрыв был в {_MONTHS_RU[worst_month.month]}: {worst_value:,.0f} ₸"
            )

    if not unpaid.empty:
        insights.append(
            f"Неоплаченных отгрузок: {len(unpaid)} на сумму {unpaid[amount_col].sum():,.0f} ₸"
        )

    return insights
