"""Модуль загрузки данных."""

import pandas as pd

# Ключевые слова для эвристического определения колонок с датами
_DATE_KEYWORDS = ("дата", "date")


def load_file(file):
    """Загружает файл (CSV/Excel) и возвращает DataFrame.

    Параметры:
        file: файловый объект, полученный из st.file_uploader
              (или путь к файлу).

    Исключения:
        ValueError: если формат файла не поддерживается или файл пуст/повреждён.
    """
    name = getattr(file, "name", str(file))
    suffix = name.lower().rsplit(".", maxsplit=1)[-1] if "." in name else ""

    try:
        if suffix == "csv":
            try:
                df = pd.read_csv(file, sep=None, engine="python", encoding="utf-8-sig")
            except UnicodeDecodeError:
                if hasattr(file, "seek"):
                    file.seek(0)
                df = pd.read_csv(file, sep=None, engine="python", encoding="cp1251")
        elif suffix in ("xlsx", "xls"):
            df = pd.read_excel(file)
        else:
            raise ValueError(
                f"Неподдерживаемый формат файла: «.{suffix}». "
                "Загрузите файл в формате CSV или Excel (.xlsx, .xls)."
            )
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(
            f"Не удалось прочитать файл «{name}». "
            f"Проверьте, что файл не повреждён и имеет корректный формат. "
            f"Ошибка: {exc}"
        ) from exc

    if df.empty:
        raise ValueError(f"Файл «{name}» пуст или не содержит данных.")

    return df


def clean_dataframe(df):
    """Приводит DataFrame к единому виду.

    - названия колонок приводятся к нижнему регистру, пробелы убираются,
      пробелы внутри названий заменяются на «_»;
    - колонки с датами конвертируются в datetime;
    - числовые колонки (в том числе записанные строками с запятой
      вместо точки) приводятся к числовому типу.

    Исключения:
        ValueError: если после очистки DataFrame оказался пустым.
    """
    if df is None or df.empty:
        raise ValueError("Нет данных для обработки: передан пустой DataFrame.")

    df = df.copy()

    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", "_", regex=True)
    )

    for col in df.columns:
        if any(keyword in col for keyword in _DATE_KEYWORDS):
            df[col] = pd.to_datetime(df[col], errors="coerce", format="mixed", dayfirst=True)
            continue

        if df[col].dtype == object:
            converted = pd.to_numeric(
                df[col].astype(str).str.replace(",", ".", regex=False).str.strip(),
                errors="coerce",
            )
            # Считаем колонку числовой, только если распозналось
            # подавляющее большинство непустых значений.
            non_null = df[col].notna().sum()
            if non_null > 0 and converted.notna().sum() / non_null >= 0.9:
                df[col] = converted

    df = df.dropna(axis=1, how="all")

    if df.empty:
        raise ValueError("После очистки данных не осталось ни одной строки/колонки.")

    return df


def get_column_info(df):
    """Определяет тип каждой колонки DataFrame.

    Возвращает словарь вида:
        {
            "date_columns": [...],
            "numeric_columns": [...],
            "text_columns": [...],
            "all_columns": {"имя_колонки": "date" | "numeric" | "text", ...},
        }
    """
    if df is None:
        raise ValueError("Нет данных: DataFrame не передан.")

    date_columns = []
    numeric_columns = []
    text_columns = []
    all_columns = {}

    for col in df.columns:
        dtype = df[col].dtype
        if pd.api.types.is_datetime64_any_dtype(dtype):
            date_columns.append(col)
            all_columns[col] = "date"
        elif pd.api.types.is_numeric_dtype(dtype):
            numeric_columns.append(col)
            all_columns[col] = "numeric"
        else:
            text_columns.append(col)
            all_columns[col] = "text"

    return {
        "date_columns": date_columns,
        "numeric_columns": numeric_columns,
        "text_columns": text_columns,
        "all_columns": all_columns,
    }
