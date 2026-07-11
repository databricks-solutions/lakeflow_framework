SELECT
    CAST(date_format(d, 'yyyyMMdd') AS INT)                  AS date_key,
    d                                                        AS date,
    year(d)                                                  AS year,
    quarter(d)                                               AS quarter,
    month(d)                                                 AS month,
    day(d)                                                   AS day,
    date_format(d, 'MMMM')                                   AS month_name,
    date_format(d, 'EEEE')                                   AS day_name,
    dayofweek(d)                                             AS day_of_week,
    weekofyear(d)                                            AS week_of_year,
    CASE WHEN dayofweek(d) IN (1, 7) THEN true ELSE false END AS is_weekend,
    fiscal_year                                             AS fiscal_year,
    fiscal_quarter                                          AS fiscal_quarter,
    fiscal_month                                            AS fiscal_month,
    concat('FY', CAST(fiscal_year AS STRING))              AS fiscal_year_label,
    concat('FY', CAST(fiscal_year AS STRING), '-Q', CAST(fiscal_quarter AS STRING)) AS fiscal_quarter_label,
    concat('FY', CAST(fiscal_year AS STRING), '-', lpad(CAST(fiscal_month AS STRING), 2, '0')) AS fiscal_period
FROM (
    SELECT
        d,
        -- Fiscal calendar starts 1 April; FY is labelled by its starting calendar year
        -- (e.g. 1 Apr 1995 - 31 Mar 1996 = FY1995). Change the start month (4) below to adjust.
        CASE WHEN month(d) >= 4 THEN year(d) ELSE year(d) - 1 END AS fiscal_year,
        CAST(floor(mod(month(d) - 4 + 12, 12) / 3) AS INT) + 1    AS fiscal_quarter,
        CAST(mod(month(d) - 4 + 12, 12) AS INT) + 1               AS fiscal_month
    FROM (SELECT explode(sequence(to_date('1992-01-01'), to_date('1998-12-31'), interval 1 day)) AS d)
)
