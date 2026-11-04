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


def _finite_number(value: Any) -> float | None:
    """Convert a scalar to a JSON-safe float, mapping NaN and infinity to null."""
    number = float(np.asarray(value).item())
    return number if math.isfinite(number) else None


def _check_coordinates(ds: xr.Dataset, latitude: float, longitude: float) -> None:
    """Reject coordinates outside the master dataset's spatial coverage."""
    lat_min = float(ds.latitude.min().item())
    lat_max = float(ds.latitude.max().item())
    lon_min = float(ds.longitude.min().item())
    lon_max = float(ds.longitude.max().item())
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
            "latitude_range": [float(ds.latitude.min().item()), float(ds.latitude.max().item())],
            "longitude_range": [float(ds.longitude.min().item()), float(ds.longitude.max().item())],
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
        actual_latitude = float(point.latitude.item())
        actual_longitude = float(point.longitude.item())
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
                    "depth_m": float(depth_data.depth.item()),
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
                "latitude": float(data.latitude.item()),
                "longitude": float(data.longitude.item()),
            }

        if "depth" in data.dims:
            if depth_m is None:
                raise ValueError("Specify depth_m when calculating thetao statistics.")
            data = data.sel(depth=depth_m, method="nearest")
            selected_depth = float(data.depth.item())
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
        valid_count = int(computed["valid_count"].item())
        if valid_count:
            mean = _finite_number(computed["mean"].item())
            minimum = _finite_number(computed["minimum"].item())
            maximum = _finite_number(computed["maximum"].item())
            standard_deviation = _finite_number(computed["standard_deviation"].item())
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


OCEAN_DATA_TOOLS = [
    get_ocean_dataset_info,
    get_ocean_values_at_point,
    get_monthly_statistics,
]
