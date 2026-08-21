"""Точка входа Streamlit-приложения sales-analytics."""

import streamlit as st

from modules.upload import load_file, clean_dataframe, get_column_info
from modules.abc_analysis import analyze_products, analyze_clients, plot_abc, get_abc_insights
from modules.cashflow import calculate_gap, get_unpaid, plot_cashflow, get_cashflow_insights
from modules.dynamics import monthly_sales, plot_dynamics, get_dynamics_insights
from modules.clients import client_summary, churn_risk, plot_clients, get_clients_insights
from modules.managers import (
    manager_summary,
    manager_monthly,
    plot_managers,
    plot_managers_trend,
    get_managers_insights,
)
from modules.ai_advisor import get_advice


def _guess_column(candidates, keywords, exclude_keywords=()):
    """Подбирает наиболее вероятную колонку по ключевым словам в названии."""
    for col in candidates:
        if any(k in col for k in keywords) and not any(k in col for k in exclude_keywords):
            return col
    return candidates[0] if candidates else None


def _select_columns(column_info):
    """Показывает в сайдбаре выбор нужных колонок и возвращает их имена."""
    date_columns = column_info["date_columns"]
    numeric_columns = column_info["numeric_columns"]
    text_columns = column_info["text_columns"]

    if not date_columns or not numeric_columns or not text_columns:
        st.sidebar.error(
            "Не удалось найти нужные типы колонок (дата, число, текст). "
            "Проверьте структуру файла."
        )
        return None

    st.sidebar.subheader("Соответствие колонок")

    date_col = st.sidebar.selectbox(
        "Дата продажи",
        date_columns,
        index=date_columns.index(_guess_column(date_columns, ["дата", "date"], ["оплат", "pay"])),
    )

    payment_options = ["— нет —"] + date_columns
    payment_guess = _guess_column(date_columns, ["оплат", "pay"])
    payment_index = payment_options.index(payment_guess) if payment_guess in payment_options else 0
    payment_col = st.sidebar.selectbox("Дата оплаты", payment_options, index=payment_index)
    payment_col = None if payment_col == "— нет —" else payment_col

    amount_col = st.sidebar.selectbox(
        "Сумма",
        numeric_columns,
        index=numeric_columns.index(_guess_column(numeric_columns, ["сумма", "amount", "sum"])),
    )

    product_col = st.sidebar.selectbox(
        "Товар",
        text_columns,
        index=text_columns.index(_guess_column(text_columns, ["товар", "product", "номенклатур"])),
    )

    client_guess_list = [c for c in text_columns if c != product_col] or text_columns
    client_col = st.sidebar.selectbox(
        "Контрагент",
        text_columns,
        index=text_columns.index(_guess_column(client_guess_list, ["контрагент", "клиент", "client", "customer"])),
    )

    manager_options = ["— нет —"] + text_columns
    manager_guess_list = [c for c in text_columns if c not in (product_col, client_col)] or text_columns
    manager_guess = _guess_column(manager_guess_list, ["менеджер", "manager", "сотрудник"])
    manager_index = manager_options.index(manager_guess) if manager_guess in manager_options else 0
    manager_col = st.sidebar.selectbox("Менеджер", manager_options, index=manager_index)
    manager_col = None if manager_col == "— нет —" else manager_col

    return {
        "date_col": date_col,
        "payment_col": payment_col,
        "amount_col": amount_col,
        "product_col": product_col,
        "client_col": client_col,
        "manager_col": manager_col,
    }


def _render_abc_tab(df, product_col, amount_col):
    products = analyze_products(df, product_col, amount_col)
    st.plotly_chart(plot_abc(products, title="ABC-анализ товаров"), use_container_width=True)
    st.dataframe(products, use_container_width=True)

    st.markdown("**Выводы:**")
    for insight in get_abc_insights(products):
        st.markdown(f"- {insight}")

    return get_abc_insights(products)


def _render_cashflow_tab(df, date_col, payment_col, amount_col):
    if payment_col is None:
        st.info("Для анализа кассового разрыва выберите колонку «Дата оплаты» в сайдбаре.")
        return []

    gap_df = calculate_gap(df, date_col, payment_col, amount_col)
    st.plotly_chart(plot_cashflow(gap_df), use_container_width=True)
    st.dataframe(gap_df, use_container_width=True)

    unpaid = get_unpaid(df, date_col, payment_col, amount_col)
    if not unpaid.empty:
        st.markdown(f"**Неоплаченные отгрузки ({len(unpaid)}):**")
        st.dataframe(unpaid, use_container_width=True)

    insights = get_cashflow_insights(df, date_col, payment_col, amount_col)
    st.markdown("**Выводы:**")
    for insight in insights:
        st.markdown(f"- {insight}")

    return insights


def _render_dynamics_tab(df, date_col, amount_col):
    monthly = monthly_sales(df, date_col, amount_col)
    st.plotly_chart(plot_dynamics(monthly), use_container_width=True)
    st.dataframe(monthly, use_container_width=True)

    insights = get_dynamics_insights(monthly)
    st.markdown("**Выводы:**")
    for insight in insights:
        st.markdown(f"- {insight}")

    return insights


def _render_clients_tab(df, client_col, amount_col, date_col):
    summary = client_summary(df, client_col, amount_col, date_col)
    st.plotly_chart(plot_clients(summary), use_container_width=True)

    st.markdown("**⚠️ Риск оттока**")
    st.dataframe(churn_risk(summary), use_container_width=True)

    insights = get_clients_insights(summary)
    st.markdown("**Выводы:**")
    for insight in insights:
        st.markdown(f"- {insight}")

    return insights


def _render_managers_tab(df, manager_col, amount_col, date_col):
    if manager_col is None:
        st.info("Для анализа менеджеров выберите колонку «Менеджер» в сайдбаре.")
        return []

    summary = manager_summary(df, manager_col, amount_col, date_col)
    monthly = manager_monthly(df, manager_col, amount_col, date_col)

    col_pie, col_table = st.columns(2)
    with col_pie:
        st.plotly_chart(plot_managers(summary), use_container_width=True)
    with col_table:
        st.dataframe(summary, use_container_width=True)

    st.plotly_chart(plot_managers_trend(monthly), use_container_width=True)

    insights = get_managers_insights(summary, monthly)
    st.markdown("**Выводы:**")
    for insight in insights:
        st.markdown(f"- {insight}")

    return insights


def _render_ai_tab(abc_insights, cashflow_insights, api_key):
    if not api_key:
        st.info("Введите Anthropic API key в сайдбаре, чтобы получить AI-рекомендации.")
        return

    if st.button("Получить рекомендации"):
        with st.spinner("Анализируем данные..."):
            advice = get_advice(abc_insights, cashflow_insights, api_key)
        st.markdown(advice)


def main():
    """Запускает основное Streamlit-приложение."""
    st.set_page_config(page_title="Аналитика продаж", page_icon="📊", layout="wide")

    st.title("📊 Аналитика продаж")
    st.caption("ABC-анализ товаров и контроль кассовых разрывов по данным о продажах")

    st.sidebar.header("Настройки")
    uploaded_file = st.sidebar.file_uploader("Загрузите файл (CSV или Excel)", type=["csv", "xlsx", "xls"])
    api_key = st.sidebar.text_input("Anthropic API key", type="password")
    analyze_clicked = st.sidebar.button("Анализировать", type="primary")

    if not uploaded_file:
        st.info("Загрузите файл с данными о продажах в сайдбаре, чтобы начать анализ.")
        return

    try:
        df = clean_dataframe(load_file(uploaded_file))
    except ValueError as exc:
        st.error(str(exc))
        return

    column_info = get_column_info(df)
    columns = _select_columns(column_info)
    if columns is None:
        return

    if analyze_clicked:
        st.session_state["analyzed"] = True

    if not st.session_state.get("analyzed"):
        st.info("Настройте колонки в сайдбаре и нажмите «Анализировать».")
        return

    tab_abc, tab_cashflow, tab_dynamics, tab_clients, tab_managers, tab_ai = st.tabs(
        ["ABC-анализ", "Кассовый разрыв", "📈 Динамика продаж", "👥 Клиенты", "🏆 Менеджеры", "AI-советы"]
    )

    with tab_abc:
        abc_insights = _render_abc_tab(df, columns["product_col"], columns["amount_col"])

    with tab_cashflow:
        cashflow_insights = _render_cashflow_tab(
            df, columns["date_col"], columns["payment_col"], columns["amount_col"]
        )

    with tab_dynamics:
        _render_dynamics_tab(df, columns["date_col"], columns["amount_col"])

    with tab_clients:
        _render_clients_tab(df, columns["client_col"], columns["amount_col"], columns["date_col"])

    with tab_managers:
        _render_managers_tab(df, columns["manager_col"], columns["amount_col"], columns["date_col"])

    with tab_ai:
        _render_ai_tab(abc_insights, cashflow_insights, api_key)


if __name__ == "__main__":
    main()
