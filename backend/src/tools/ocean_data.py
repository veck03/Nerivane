"""LangChain tools for querying the master ocean Zarr dataset.

Every tool in this module reads only ``ocean_q1_2020.zarr``. Calculations use
xarray's NaN-aware methods so missing ocean-grid cells do not affect results.
"""

import calendar
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import xarray as xr
from langchain_core.tools import tool

BACKEND_DIR = Path(__file__).resolve().parents[2]
MASTER_DATASET_PATH = (
    BACKEND_DIR.parent
    / "data"
    / "legacy_dataset"
    / "processed"
    / "ocean_q1_2020.zarr"
)


def _open_master_dataset() -> xr.Dataset:
    """Open the one approved data source, raising a useful error if absent."""
    if not MASTER_DATASET_PATH.is_dir():
        raise FileNotFoundError(
            f"Master dataset not found at {MASTER_DATASET_PATH}. "
            "Expected data/legacy_dataset/processed/ocean_q1_2020.zarr."
        )
    return xr.open_zarr(MASTER_DATASET_PATH, consolidated=None)


def _json_result(value: dict[str, Any]) -> str:
    """Serialize a tool result while converting non-finite numbers to null."""
    return json.dumps(value, indent=2, allow_nan=False, default=str)


def _scalar_value(value: Any) -> Any:
    """Materialize a scalar before extracting it, including Dask-backed values."""
    data = getattr(value, "data", value)
    compute = getattr(data, "compute", None)
    if callable(compute):
        data = compute()
    array = np.asarray(data)
    if array.size != 1:
        raise ValueError("Expected a scalar dataset value.")
    return array.reshape(-1)[0].item()


def _finite_number(value: Any) -> float | None:
    """Convert a scalar to a JSON-safe float, mapping NaN and infinity to null."""
    number = float(_scalar_value(value))
    return number if math.isfinite(number) else None


def _check_coordinates(ds: xr.Dataset, latitude: float, longitude: float) -> None:
    """Reject coordinates outside the master dataset's spatial coverage."""
    lat_min = float(_scalar_value(ds.latitude.min()))
    lat_max = float(_scalar_value(ds.latitude.max()))
    lon_min = float(_scalar_value(ds.longitude.min()))
    lon_max = float(_scalar_value(ds.longitude.max()))
    if not lat_min <= latitude <= lat_max or not lon_min <= longitude <= lon_max:
        raise ValueError(
            f"Requested point ({latitude}, {longitude}) is outside coverage: "
            f"latitude {lat_min}..{lat_max}, longitude {lon_min}..{lon_max}."
        )


@tool
def get_ocean_dataset_info() -> str:
    """Describe the available variables, units, time span, and grid coverage.

    Use this first when you need to know which measurements or dates are
    available. Information comes only from the master ocean dataset.
    """
    with _open_master_dataset() as ds:
        variables = {}
        for name, variable in ds.data_vars.items():
            variables[name] = {
                "dimensions": list(variable.dims),
                "shape": list(variable.shape),
                "units": variable.attrs.get("units"),
                "description": variable.attrs.get("long_name")
                or variable.attrs.get("standard_name"),
            }
        info = {
            "dataset": MASTER_DATASET_PATH.name,
            "time_start": str(ds.time.min().values),
            "time_end": str(ds.time.max().values),
            "time_steps": int(ds.sizes["time"]),
            "latitude_range": [float(_scalar_value(ds.latitude.min())), float(_scalar_value(ds.latitude.max()))],
            "longitude_range": [float(_scalar_value(ds.longitude.min())), float(_scalar_value(ds.longitude.max()))],
            "depth_levels_m": [float(value) for value in ds.depth.values]
            if "depth" in ds.coords and ds.depth.ndim == 1
            else [],
            "variables": variables,
        }
    return _json_result(info)


@tool
def get_ocean_values_at_point(
    latitude: float,
    longitude: float,
    date: str,
    depth_m: float | None = None,
) -> str:
    """Get master-dataset measurements at the nearest grid cell and exact date.

    Args:
        latitude: Requested latitude in decimal degrees.
        longitude: Requested longitude in decimal degrees east.
        date: Exact date in YYYY-MM-DD format. Dates outside the dataset are not interpolated.
        depth_m: Optional depth for thetao. If omitted, thetao uses its shallowest depth level.

    Returns the selected grid coordinates and all available surface variables,
    plus thetao at the requested or shallowest depth. Missing values are null.
    """
    with _open_master_dataset() as ds:
        _check_coordinates(ds, latitude, longitude)
        try:
            day = ds.sel(time=np.datetime64(date))
        except (KeyError, ValueError) as error:
            raise ValueError(
                f"Date {date!r} is not an available exact time step. "
                f"Coverage is {str(ds.time.min().values)} through {str(ds.time.max().values)}."
            ) from error
        point = day.sel(latitude=latitude, longitude=longitude, method="nearest")
        actual_latitude = float(_scalar_value(point.latitude))
        actual_longitude = float(_scalar_value(point.longitude))
        values: dict[str, Any] = {}
        for name, variable in ds.data_vars.items():
            if "depth" in variable.dims:
                selected_depth = (
                    float(ds.depth.values[0])
                    if depth_m is None
                    else depth_m
                )
                depth_data = point[name].sel(depth=selected_depth, method="nearest")
                values[name] = {
                    "value": _finite_number(depth_data.values),
                    "depth_m": float(_scalar_value(depth_data.depth)),
                    "units": variable.attrs.get("units"),
                }
            else:
                values[name] = {
                    "value": _finite_number(point[name].values),
                    "units": variable.attrs.get("units"),
                }
        result = {
            "dataset": MASTER_DATASET_PATH.name,
            "requested_point": {"latitude": latitude, "longitude": longitude},
            "selected_grid_point": {
                "latitude": actual_latitude,
                "longitude": actual_longitude,
            },
            "date": str(point.time.values),
            "values": values,
            "missing_values_note": "null means the selected grid cell is NaN or unavailable.",
        }
    return _json_result(result)


@tool
def get_monthly_statistics(
    variable: str,
    year: int,
    month: int,
    latitude: float | None = None,
    longitude: float | None = None,
    depth_m: float | None = None,
) -> str:
    """Calculate NaN-aware monthly mean, minimum, maximum, and standard deviation.

    Args:
        variable: A variable listed by get_ocean_dataset_info, such as sst, sss,
            sla, current_u, current_v, wind_u, wind_v, or thetao.
        year: Year in the dataset (currently 2020).
        month: Month number from 1 to 12 (the master store contains January to March).
        latitude: Optional latitude. Supply together with longitude to average over time
            at the nearest grid cell; omit both for a mean over the whole grid.
        longitude: Optional longitude, used with latitude.
        depth_m: Required for thetao; selects the nearest stored depth level.

    With no location, statistics include all valid grid cells and dates in the month.
    With a location, they include valid daily values at that nearest grid cell.
    NaN values are skipped, and valid_observation_count reports the remaining samples.
    """
    if month < 1 or month > 12:
        raise ValueError("month must be between 1 and 12")
    if (latitude is None) != (longitude is None):
        raise ValueError("Provide both latitude and longitude, or neither.")

    month_start = f"{year:04d}-{month:02d}-01"
    month_end = f"{year:04d}-{month:02d}-{calendar.monthrange(year, month)[1]:02d}"
    with _open_master_dataset() as ds:
        if variable not in ds.data_vars:
            raise ValueError(
                f"Unknown variable {variable!r}. Available variables: "
                f"{', '.join(ds.data_vars)}."
            )
        data = ds[variable].sel(time=slice(month_start, month_end))
        if data.sizes.get("time", 0) == 0:
            raise ValueError(
                f"No data for {year:04d}-{month:02d}. The master dataset covers "
                f"{str(ds.time.min().values)} through {str(ds.time.max().values)}."
            )

        selected_grid_point = None
        selected_depth = None
        if latitude is not None and longitude is not None:
            _check_coordinates(ds, latitude, longitude)
            data = data.sel(latitude=latitude, longitude=longitude, method="nearest")
            selected_grid_point = {
                "latitude": float(_scalar_value(data.latitude)),
                "longitude": float(_scalar_value(data.longitude)),
            }

        if "depth" in data.dims:
            if depth_m is None:
                raise ValueError("Specify depth_m when calculating thetao statistics.")
            data = data.sel(depth=depth_m, method="nearest")
            selected_depth = float(_scalar_value(data.depth))
        elif depth_m is not None:
            raise ValueError(f"{variable!r} has no depth dimension; omit depth_m.")

        if selected_grid_point:
            mean_data = data.mean(skipna=True)
            standard_deviation_data = data.std(skipna=True)
            mean_method = "arithmetic mean over valid daily values at the selected grid point"
        else:
            # A regular latitude/longitude grid represents smaller cells toward
            # the poles, so cosine-latitude weights better represent area means.
            latitude_weights = np.cos(np.deg2rad(ds.latitude))
            mean_data = data.weighted(latitude_weights).mean(skipna=True)
            standard_deviation_data = data.weighted(latitude_weights).std(skipna=True)
            mean_method = "cosine-of-latitude area-weighted mean across valid grid cells and dates"

        computed = xr.Dataset(
            {
                "mean": mean_data,
                "minimum": data.min(skipna=True),
                "maximum": data.max(skipna=True),
                "standard_deviation": standard_deviation_data,
                "valid_count": data.count(),
            }
        ).compute()
        valid_count = int(_scalar_value(computed["valid_count"]))
        if valid_count:
            mean = _finite_number(computed["mean"])
            minimum = _finite_number(computed["minimum"])
            maximum = _finite_number(computed["maximum"])
            standard_deviation = _finite_number(computed["standard_deviation"])
        else:
            mean = minimum = maximum = standard_deviation = None

        result = {
            "dataset": MASTER_DATASET_PATH.name,
            "variable": variable,
            "units": ds[variable].attrs.get("units"),
            "period": f"{year:04d}-{month:02d}",
            "aggregation_scope": "nearest grid point over valid daily values"
            if selected_grid_point
            else "all grid cells and valid daily values",
            "mean_method": mean_method,
            "selected_grid_point": selected_grid_point,
            "selected_depth_m": selected_depth,
            "mean": mean,
            "minimum": minimum,
            "maximum": maximum,
            "standard_deviation": standard_deviation,
            "valid_observation_count": valid_count,
            "nan_values_skipped": True,
        }
    return _json_result(result)


@tool
def get_monthly_statistics_for_months(
    variable: str,
    year: int,
    months: list[int],
    latitude: float | None = None,
    longitude: float | None = None,
    depth_m: float | None = None,
) -> str:
    """Calculate monthly statistics for several months in one tool call.

    Use this for monthly comparisons or a chart across months. It calls the existing
    single-month statistics function for every requested month, preserving its
    NaN-aware mean and area-weighted aggregation behavior.

    Args:
        variable: Dataset variable such as sst, sss, sla, current_u, wind_u, or thetao.
        year: Year in the dataset (currently 2020).
        months: Array of month numbers, for example [1, 2, 3].
        latitude: Optional latitude. Supply together with longitude for a nearest grid point.
        longitude: Optional longitude.
        depth_m: Required for depth-dependent variables such as thetao.
    """
    if not months:
        raise ValueError("Provide at least one month.")
    if len(months) > 12:
        raise ValueError("Request no more than 12 months at a time.")
    if len(set(months)) != len(months):
        raise ValueError("Month values must not be duplicated.")
    if (latitude is None) != (longitude is None):
        raise ValueError("Provide both latitude and longitude, or neither.")

    monthly_results = []
    for month in months:
        arguments = {
            "variable": variable,
            "year": year,
            "month": month,
            "latitude": latitude,
            "longitude": longitude,
            "depth_m": depth_m,
        }
        try:
            output = get_monthly_statistics.invoke(arguments)
            monthly_results.append(json.loads(output))
        except Exception as error:
            monthly_results.append({
                "period": f"{year:04d}-{month:02d}" if 1 <= month <= 12 else str(month),
                "variable": variable,
                "error": str(error),
            })

    units = next((result.get("units") for result in monthly_results if result.get("units")), None)
    labels = [result.get("period", str(month)) for month, result in zip(months, monthly_results)]
    values = [result.get("mean") for result in monthly_results]
    errors = [result.get("error") for result in monthly_results]
    result = {
        "dataset": MASTER_DATASET_PATH.name,
        "variable": variable,
        "units": units,
        "monthly_results": monthly_results,
        "failed_months": [label for label, error in zip(labels, errors) if error],
        "chart_data": {
            "type": "bar",
            "title": f"Monthly mean {variable}",
            "variable": variable,
            "units": units,
            "labels": labels,
            "values": values,
        },
    }
    return _json_result(result)


@tool
def get_daily_average_series(
    variable: str,
    year: int,
    month: int,
    days: list[int] | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    depth_m: float | None = None,
) -> str:
    """Return one daily mean per date in a month as line-chart data.

    Args:
        variable: Dataset variable such as sst, sss, sla, current_u, or thetao.
        year: Year in the dataset (currently 2020).
        month: Month number from 1 to 12.
        days: Optional array of day numbers to include. If omitted, use every available day.
        latitude: Optional latitude. Supply together with longitude for a nearest grid point.
        longitude: Optional longitude.
        depth_m: Required for depth-dependent variables such as thetao.

    Without a location, each point is the cosine-of-latitude area-weighted daily
    mean across valid grid cells. At a location, each point is the value at the
    nearest grid cell. NaNs are skipped, and missing days remain chart gaps.
    """
    if month < 1 or month > 12:
        raise ValueError("month must be between 1 and 12")
    if (latitude is None) != (longitude is None):
        raise ValueError("Provide both latitude and longitude, or neither.")
    month_days = calendar.monthrange(year, month)[1]
    if days is not None:
        if not days:
            raise ValueError("Provide at least one day or omit days to use the full month.")
        if len(days) > month_days or len(set(days)) != len(days):
            raise ValueError("Day values must be unique and fit within the selected month.")
        if any(day < 1 or day > month_days for day in days):
            raise ValueError(f"Days for {year:04d}-{month:02d} must be between 1 and {month_days}.")

    month_start = f"{year:04d}-{month:02d}-01"
    month_end = f"{year:04d}-{month:02d}-{month_days:02d}"
    with _open_master_dataset() as ds:
        if variable not in ds.data_vars:
            raise ValueError(f"Unknown variable {variable!r}. Available variables: {', '.join(ds.data_vars)}.")
        data = ds[variable].sel(time=slice(month_start, month_end))
        if data.sizes.get("time", 0) == 0:
            raise ValueError(f"No data for {year:04d}-{month:02d}.")

        selected_grid_point = None
        if latitude is not None and longitude is not None:
            _check_coordinates(ds, latitude, longitude)
            data = data.sel(latitude=latitude, longitude=longitude, method="nearest")
            selected_grid_point = {
                "latitude": float(_scalar_value(data.latitude)),
                "longitude": float(_scalar_value(data.longitude)),
            }

        selected_depth = None
        if "depth" in data.dims:
            if depth_m is None:
                raise ValueError(f"Specify depth_m for depth-dependent variable {variable!r}.")
            data = data.sel(depth=depth_m, method="nearest")
            selected_depth = float(_scalar_value(data.depth))
        elif depth_m is not None:
            raise ValueError(f"{variable!r} has no depth dimension; omit depth_m.")

        if days is not None:
            data = data.where(data.time.dt.day.isin(days), drop=True)
        if data.sizes.get("time", 0) == 0:
            raise ValueError("No dataset observations were found for the requested days.")

        if selected_grid_point:
            daily_means = data
            daily_counts = data.count()
            scope = "values at the nearest grid point for each valid day"
        else:
            weights = np.cos(np.deg2rad(ds.latitude))
            daily_means = data.weighted(weights).mean(dim=("latitude", "longitude"), skipna=True)
            daily_counts = data.count(dim=("latitude", "longitude"))
            scope = "cosine-of-latitude area-weighted mean across valid grid cells for each day"

        computed = xr.Dataset({"mean": daily_means, "count": daily_counts}).compute()
        labels = [str(np.datetime_as_string(value, unit="D")) for value in computed.time.values]
        values = [_finite_number(value) for value in computed["mean"].values]
        counts = [int(value) for value in np.asarray(computed["count"].values).reshape(-1)]
        result = {
            "dataset": MASTER_DATASET_PATH.name,
            "variable": variable,
            "units": ds[variable].attrs.get("units"),
            "period": f"{year:04d}-{month:02d}",
            "selected_days": labels,
            "selected_grid_point": selected_grid_point,
            "selected_depth_m": selected_depth,
            "aggregation_scope": scope,
            "nan_values_skipped": True,
            "valid_observation_counts": counts,
            "chart_data": {
                "type": "line",
                "title": f"Daily mean {variable} · {year:04d}-{month:02d}",
                "variable": variable,
                "units": ds[variable].attrs.get("units"),
                "labels": labels,
                "values": values,
            },
        }
    return _json_result(result)


@tool
def get_ocean_monthly_series(
    variable: str,
    latitude: float | None = None,
    longitude: float | None = None,
    depth_m: float | None = None,
) -> str:
    """Return Q1 monthly means for a variable, suitable for a compact bar chart.

    Args:
        variable: Dataset variable such as sst, sss, sla, current_u, wind_u, or thetao.
        latitude: Optional latitude. Supply together with longitude for a nearest grid point.
        longitude: Optional longitude, used together with latitude.
        depth_m: Required for depth-dependent variables such as thetao.

    Without a location, values are cosine-of-latitude area-weighted means over valid
    grid cells and days. With a location, values are daily means at the nearest cell.
    The master dataset currently covers January through March 2020. NaNs are skipped.
    """
    if (latitude is None) != (longitude is None):
        raise ValueError("Provide both latitude and longitude, or neither.")

    with _open_master_dataset() as ds:
        if variable not in ds.data_vars:
            raise ValueError(f"Unknown variable {variable!r}. Available variables: {', '.join(ds.data_vars)}.")
        data = ds[variable]
        if "depth" in data.dims:
            if depth_m is None:
                raise ValueError(f"Specify depth_m for depth-dependent variable {variable!r}.")
            data = data.sel(depth=depth_m, method="nearest")
            selected_depth = float(_scalar_value(data.depth))
        else:
            if depth_m is not None:
                raise ValueError(f"{variable!r} has no depth dimension; omit depth_m.")
            selected_depth = None

        selected_grid_point = None
        if latitude is not None and longitude is not None:
            _check_coordinates(ds, latitude, longitude)
            data = data.sel(latitude=latitude, longitude=longitude, method="nearest")
            selected_grid_point = {
                "latitude": float(_scalar_value(data.latitude)),
                "longitude": float(_scalar_value(data.longitude)),
            }

        month_numbers = sorted({int(value) for value in ds.time.dt.month.values.tolist()})
        labels: list[str] = []
        monthly_results = []
        for month in month_numbers:
            monthly_data = data.where(data.time.dt.month == month, drop=True)
            labels.append(f"2020-{month:02d}")
            if selected_grid_point:
                monthly_mean = monthly_data.mean(dim="time", skipna=True)
            else:
                weights = np.cos(np.deg2rad(ds.latitude))
                monthly_mean = monthly_data.weighted(weights).mean(
                    dim=("time", "latitude", "longitude"), skipna=True
                )
            monthly_results.append(xr.Dataset({"mean": monthly_mean, "count": monthly_data.count()}))

        computed = xr.concat(monthly_results, dim="month").compute()
        means = [_finite_number(value) for value in computed["mean"].values]
        counts = [int(value) for value in computed["count"].values]

        result = {
            "dataset": MASTER_DATASET_PATH.name,
            "variable": variable,
            "units": ds[variable].attrs.get("units"),
            "selected_grid_point": selected_grid_point,
            "selected_depth_m": selected_depth,
            "aggregation_scope": "nearest grid point over valid daily values" if selected_grid_point else "cosine-of-latitude area-weighted mean over valid grid cells and days",
            "nan_values_skipped": True,
            "valid_observation_counts": counts,
            "chart_data": {
                "type": "bar",
                "title": f"Monthly mean {variable}",
                "variable": variable,
                "units": ds[variable].attrs.get("units"),
                "labels": labels,
                "values": means,
            },
        }
    return _json_result(result)


@tool
def get_ocean_daily_series_at_point(
    variable: str,
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    depth_m: float | None = None,
) -> str:
    """Return daily values for one variable at the nearest grid point for a line chart.

    Args:
        variable: Dataset variable such as sst, sss, sla, current_u, wind_u, or thetao.
        latitude: Requested latitude in decimal degrees.
        longitude: Requested longitude in decimal degrees east.
        start_date: Inclusive start date (YYYY-MM-DD).
        end_date: Inclusive end date (YYYY-MM-DD). The range is limited to 366 time steps.
        depth_m: Required for depth-dependent variables such as thetao.

    Missing measurements are returned as null and should appear as gaps in the chart.
    The tool reads only the requested variable and selected grid point.
    """
    if (latitude is None) or (longitude is None):
        raise ValueError("Provide both latitude and longitude.")
    try:
        start = np.datetime64(start_date, "D")
        end = np.datetime64(end_date, "D")
    except (TypeError, ValueError) as error:
        raise ValueError("Dates must use YYYY-MM-DD format.") from error
    if end < start:
        raise ValueError("end_date must be on or after start_date.")
    if int((end - start) / np.timedelta64(1, "D")) + 1 > 366:
        raise ValueError("Choose a date range of 366 days or less.")

    with _open_master_dataset() as ds:
        if variable not in ds.data_vars:
            raise ValueError(f"Unknown variable {variable!r}. Available variables: {', '.join(ds.data_vars)}.")
        _check_coordinates(ds, latitude, longitude)
        data = ds[variable].sel(time=slice(start, end))
        if data.sizes.get("time", 0) == 0:
            raise ValueError("No dataset observations fall within the requested date range.")
        data = data.sel(latitude=latitude, longitude=longitude, method="nearest")
        selected_depth = None
        if "depth" in data.dims:
            if depth_m is None:
                raise ValueError(f"Specify depth_m for depth-dependent variable {variable!r}.")
            data = data.sel(depth=depth_m, method="nearest")
            selected_depth = float(_scalar_value(data.depth))
        elif depth_m is not None:
            raise ValueError(f"{variable!r} has no depth dimension; omit depth_m.")

        values = np.asarray(data.compute().values).reshape(-1)
        labels = [str(np.datetime_as_string(value, unit="D")) for value in data.time.values]
        series = [_finite_number(value) for value in values]
        result = {
            "dataset": MASTER_DATASET_PATH.name,
            "variable": variable,
            "units": ds[variable].attrs.get("units"),
            "requested_point": {"latitude": latitude, "longitude": longitude},
            "selected_grid_point": {
                "latitude": float(_scalar_value(data.latitude)),
                "longitude": float(_scalar_value(data.longitude)),
            },
            "selected_depth_m": selected_depth,
            "period": {"start": labels[0], "end": labels[-1]},
            "valid_observation_count": sum(value is not None for value in series),
            "nan_values_skipped": True,
            "chart_data": {
                "type": "line",
                "title": f"{variable} over time at selected point",
                "variable": variable,
                "units": ds[variable].attrs.get("units"),
                "labels": labels,
                "values": series,
            },
        }
    return _json_result(result)


OCEAN_DATA_TOOLS = [
    get_ocean_dataset_info,
    get_ocean_values_at_point,
    get_monthly_statistics,
    get_monthly_statistics_for_months,
    get_daily_average_series,
    get_ocean_daily_series_at_point,
]
