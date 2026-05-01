from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

try:
    import yfinance as yf
except Exception:  # optional
    yf = None

REQUIRED_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]


@dataclass
class ValidationResult:
    data: pd.DataFrame
    report: dict[str, Any]


class InputAdapter:
    @staticmethod
    def from_manual_rows(rows: list[dict[str, Any]]) -> pd.DataFrame:
        return pd.DataFrame(rows)

    @staticmethod
    def from_upload(content: bytes, filename: str, trusted_pickle: bool = False) -> tuple[pd.DataFrame, list[str]]:
        suffix = Path(filename).suffix.lower()
        warnings: list[str] = []
        if suffix == ".csv":
            return pd.read_csv(io.BytesIO(content)), warnings
        if suffix in {".xlsx", ".xls"}:
            return pd.read_excel(io.BytesIO(content)), warnings
        if suffix == ".parquet":
            return pd.read_parquet(io.BytesIO(content)), warnings
        if suffix in {".pkl", ".pickle"}:
            if not trusted_pickle:
                raise ValueError("Pickle upload blocked: set trusted_pickle=true only for trusted local files.")
            warnings.append("Trusted pickle accepted. Never use untrusted pickle files.")
            return pd.read_pickle(io.BytesIO(content)), warnings
        raise ValueError(f"Unsupported file type: {suffix}")

    @staticmethod
    def from_yfinance(symbol: str, period: str, interval: str) -> tuple[pd.DataFrame, list[str]]:
        if yf is None:
            raise ValueError("yfinance unavailable. Install yfinance to enable provider fetch.")
        df = yf.download(symbol, period=period, interval=interval, auto_adjust=False, progress=False)
        df = df.reset_index()
        warnings: list[str] = []
        return df, warnings


class DataEngine:
    @staticmethod
    def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
        renamed = {col: str(col).strip() for col in df.columns}
        df = df.rename(columns=renamed)
        if "Datetime" in df.columns and "Date" not in df.columns:
            df = df.rename(columns={"Datetime": "Date"})
        if "AdjClose" in df.columns and "Adj Close" not in df.columns:
            df = df.rename(columns={"AdjClose": "Adj Close"})
        if "Adj_Close" in df.columns and "Adj Close" not in df.columns:
            df = df.rename(columns={"Adj_Close": "Adj Close"})
        return df

    @staticmethod
    def normalize_market_data(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
        warnings: list[str] = []
        df = DataEngine._normalize_columns(df.copy())
        if "Adj Close" not in df.columns and "Close" in df.columns:
            df["Adj Close"] = df["Close"]
            warnings.append("Adj Close missing: fallback copied from Close.")
        existing = [c for c in REQUIRED_COLUMNS if c in df.columns]
        normalized = df[existing].copy()
        if "Date" in normalized.columns:
            normalized["Date"] = pd.to_datetime(normalized["Date"], errors="coerce")
        for c in ["Open", "High", "Low", "Close", "Adj Close", "Volume"]:
            if c in normalized.columns:
                normalized[c] = pd.to_numeric(normalized[c], errors="coerce")
        return normalized, warnings

    @staticmethod
    def validate(df: pd.DataFrame, warnings: list[str] | None = None) -> ValidationResult:
        warnings = list(warnings or [])
        normalized, norm_warnings = DataEngine.normalize_market_data(df)
        warnings.extend(norm_warnings)

        raw_rows = int(len(df))
        cleaned = normalized.dropna(subset=["Date"]).copy() if "Date" in normalized.columns else normalized.copy()
        cleaned_rows = int(len(cleaned))

        detected_columns = list(df.columns)
        missing_columns = [c for c in REQUIRED_COLUMNS if c not in normalized.columns]

        duplicate_timestamps = 0
        if "Date" in cleaned.columns:
            duplicate_timestamps = int(cleaned["Date"].duplicated().sum())

        invalid_high_low_rows = 0
        if all(c in cleaned.columns for c in ["High", "Low"]):
            invalid_high_low_rows = int((cleaned["High"] < cleaned["Low"]).sum())

        non_positive_price_rows = 0
        price_cols = [c for c in ["Open", "High", "Low", "Close", "Adj Close"] if c in cleaned.columns]
        if price_cols:
            non_positive_price_rows = int((cleaned[price_cols] <= 0).any(axis=1).sum())

        missing_value_counts = {c: int(cleaned[c].isna().sum()) for c in cleaned.columns}

        date_range = {"start": None, "end": None}
        if "Date" in cleaned.columns and not cleaned["Date"].dropna().empty:
            date_range = {
                "start": cleaned["Date"].min().isoformat(),
                "end": cleaned["Date"].max().isoformat(),
            }

        valid = (
            len(missing_columns) == 0
            and duplicate_timestamps == 0
            and invalid_high_low_rows == 0
            and non_positive_price_rows == 0
            and cleaned_rows > 0
        )

        preview = cleaned.head(20).copy()
        if "Date" in preview.columns:
            preview["Date"] = preview["Date"].astype(str)
        preview_records = preview.where(pd.notna(preview), None).to_dict(orient="records")

        report = {
            "raw_rows": raw_rows,
            "cleaned_rows": cleaned_rows,
            "detected_columns": detected_columns,
            "missing_columns": missing_columns,
            "duplicate_timestamps": duplicate_timestamps,
            "invalid_high_low_rows": invalid_high_low_rows,
            "non_positive_price_rows": non_positive_price_rows,
            "missing_value_counts": missing_value_counts,
            "date_range": date_range,
            "warnings": warnings,
            "valid": valid,
            "preview": preview_records,
        }
        return ValidationResult(data=cleaned, report=report)
