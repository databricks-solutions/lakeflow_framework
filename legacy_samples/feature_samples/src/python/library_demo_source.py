"""
Python source demonstrating cluster library usage via src/libraries/.

Uses the ``phonenumbers`` cluster library (installed via ``environment.dependencies``
from the wheel in ``src/libraries/``) directly on the driver to normalise phone
strings before creating the Spark DataFrame. No UDF required.
"""
from pyspark.sql import DataFrame, SparkSession
from typing import Dict

import phonenumbers


def _to_e164(raw: str, default_region: str = "US") -> str | None:
    """Return E.164 format for raw, or None if unparseable/invalid."""
    try:
        parsed = phonenumbers.parse(raw, default_region)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        pass
    return None


def get_phone_demo(spark: SparkSession, tokens: Dict) -> DataFrame:
    """
    Generate a demo DataFrame of raw phone strings with their E.164 equivalents.

    phonenumbers is called on the driver to pre-compute normalised values before
    the DataFrame is created — no UDF or executor-side import needed.
    """
    raw_phones = [
        (1, "+1 (650) 555-1234"),
        (2, "0044 20 7946 0958"),
        (3, "invalid-phone"),
        (4, "(212) 555-4567"),
        (5, "+61 2 9876 5432"),
    ]

    data = [(id_, raw, _to_e164(raw)) for id_, raw in raw_phones]
    return spark.createDataFrame(data, "id INT, raw_phone STRING, phone_e164 STRING")
