"""Tests asdf implementations of core module."""
import numpy as np
import pandas as pd
import pytest
import xarray as xr
from asdf import ValidationError
from scipy.spatial.transform import Rotation

import weldx.transformations as tf
from weldx.asdf.utils import _write_buffer, _write_read_buffer
from weldx.constants import WELDX_QUANTITY as Q_
from weldx.core import MathematicalExpression as ME  # nopep8
from weldx.core import TimeSeries
from weldx.transformations import WXRotation

# WXRotation ---------------------------------------------------------------------
_base_rotation = Rotation.from_euler(
    seq="xyz", angles=[[10, 20, 60], [25, 50, 175]], degrees=True
)


@pytest.mark.parametrize(
    "inputs",
    [
        _base_rotation,
        WXRotation.from_quat(_base_rotation.as_quat()),
        WXRotation.from_matrix(_base_rotation.as_matrix()),
        WXRotation.from_rotvec(_base_rotation.as_rotvec()),
        WXRotation.from_euler(seq="xyz", angles=[10, 20, 60], degrees=True),
        WXRotation.from_euler(seq="xyz", angles=[0.2, 1.3, 3.14], degrees=False),
        WXRotation.from_euler(seq="XYZ", angles=[10, 20, 60], degrees=True),
        WXRotation.from_euler(seq="y", angles=[10, 60, 40, 90], degrees=True),
        WXRotation.from_euler(seq="Z", angles=[10, 60, 40, 90], degrees=True),
        WXRotation.from_euler(
            seq="xy", angles=[[10, 10], [60, 60], [40, 40], [70, 75]], degrees=True
        ),
    ],
)
def test_rotation(inputs):
    data = _write_read_buffer({"rot": inputs})
    assert np.allclose(data["rot"].as_quat(), inputs.as_quat())


def test_rotation_euler_exception():
    with pytest.raises(ValueError):
        WXRotation.from_euler(seq="XyZ", angles=[10, 20, 60], degrees=True)


# xarray.DataArray ---------------------------------------------------------------------
def get_xarray_example_data_array():
    """
    Get an xarray.DataArray for test purposes.

    Returns
    -------
    xarray.DataArray
        DataArray for test purposes

    """
    data = np.array([[0, 1], [2, 3]])

    time_labels = ["2020-05-01", "2020-05-03"]
    d1 = np.array([-1, 1])
    d2 = pd.DatetimeIndex(time_labels)
    coords = {"d1": d1, "d2": d2, "time_labels": (["d2"], time_labels)}

    dax = xr.DataArray(data=data, dims=["d1", "d2"], coords=coords)

    dax.attrs = {"answer": 42}

    return dax


@pytest.mark.parametrize("copy_arrays", [True, False])
@pytest.mark.parametrize("lazy_load", [True, False])
def test_xarray_data_array(copy_arrays, lazy_load):
    """Test ASDF read/write of xarray.DataArray."""
    dax = get_xarray_example_data_array()
    tree = {"dax": dax}
    dax_file = _write_read_buffer(
        tree, open_kwargs={"copy_arrays": copy_arrays, "lazy_load": lazy_load}
    )["dax"]
    assert dax.identical(dax_file)


# xarray.Dataset ---------------------------------------------------------------------
def get_xarray_example_dataset():
    """
    Get an xarray.Dataset for test purposes.

    Returns
    -------
        Dataset for test purposes
    """

    temp_data = [
        [[15.0, 16.0, 17.0], [18.0, 19.0, 20.0]],
        [[21.0, 22.0, 23.0], [24.0, 25.0, 26.0]],
    ]
    temp = Q_(temp_data, "°C")
    precipitation = [
        [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]],
        [[7.0, 8.0, 9.0], [10.0, 11.0, 12.0]],
    ]
    lon = [[-99.83, -99.32], [-99.79, -99.23]]
    lat = [[42.25, 42.21], [42.63, 42.59]]

    dsx = xr.Dataset(
        {
            "temperature": (["x", "y", "time"], temp),
            "precipitation": (["x", "y", "time"], precipitation),
        },
        coords={
            "lon": (["x", "y"], lon),
            "lat": (["x", "y"], lat),
            "time": pd.date_range("2014-09-06", periods=3),
            "time_labels": (["time"], ["2014-09-06", "2014-09-09", "2014-09-12"]),
            "reference_time": pd.Timestamp("2014-09-05"),
        },
    )
    dsx.attrs = {"temperature": "Celsius"}
    return dsx


@pytest.mark.parametrize("copy_arrays", [True, False])
@pytest.mark.parametrize("lazy_load", [True, False])
def test_xarray_dataset(copy_arrays, lazy_load):
    dsx = get_xarray_example_dataset()
    tree = {"dsx": dsx}
    dsx_file = _write_read_buffer(
        tree, open_kwargs={"copy_arrays": copy_arrays, "lazy_load": lazy_load}
    )["dsx"]
    assert dsx.identical(dsx_file)


# weldx.transformations.LocalCoordinateSystem ------------------------------------------
def get_local_coordinate_system(time_dep_orientation: bool, time_dep_coordinates: bool):
    """
    Get a local coordinate system.

    Parameters
    ----------
    time_dep_orientation :
        If True, the coordinate system has a time dependent orientation.
    time_dep_coordinates :
        If True, the coordinate system has a time dependent coordinates.

    Returns
    -------
    weldx.transformations.LocalCoordinateSystem:
        A local coordinate system

    """
    if not time_dep_coordinates:
        coords = Q_(np.asarray([2.0, 5.0, 1.0]), "mm")
    else:
        coords = Q_(
            np.asarray(
                [[2.0, 5.0, 1.0], [1.0, -4.0, 1.2], [0.3, 4.4, 4.2], [1.1, 2.3, 0.2]]
            ),
            "mm",
        )

    if not time_dep_orientation:
        orientation = tf.rotation_matrix_z(np.pi / 3)
    else:
        orientation = tf.rotation_matrix_z(np.pi / 2 * np.array([1, 2, 3, 4]))

    if not time_dep_orientation and not time_dep_coordinates:
        return tf.LocalCoordinateSystem(orientation=orientation, coordinates=coords)

    time = pd.DatetimeIndex(["2000-01-01", "2000-01-02", "2000-01-03", "2000-01-04"])
    return tf.LocalCoordinateSystem(
        orientation=orientation, coordinates=coords, time=time
    )


@pytest.mark.parametrize("time_dep_orientation", [False, True])
@pytest.mark.parametrize("time_dep_coordinates", [False, True])
@pytest.mark.parametrize("copy_arrays", [True, False])
@pytest.mark.parametrize("lazy_load", [True, False])
def test_local_coordinate_system(
    time_dep_orientation, time_dep_coordinates, copy_arrays, lazy_load
):
    """Test (de)serialization of LocalCoordinateSystem in ASDF."""
    lcs = get_local_coordinate_system(time_dep_orientation, time_dep_coordinates)
    data = _write_read_buffer(
        {"lcs": lcs}, open_kwargs={"copy_arrays": copy_arrays, "lazy_load": lazy_load}
    )
    assert data["lcs"] == lcs


def test_local_coordinate_system_shape_violation():
    """Test if the shape validators work as expected."""
    # coordinates have wrong shape ------------------------
    orientation = xr.DataArray(
        data=[[1, 2, 3], [4, 5, 6], [7, 8, 9]],
        dims=["u", "v"],
        coords={"u": ["x", "y", "z"], "v": [0, 1, 2]},
    )
    coordinates = xr.DataArray(data=[1, 2], dims=["c"], coords={"c": ["x", "y"]},)
    lcs = tf.LocalCoordinateSystem(
        orientation=orientation, coordinates=coordinates, construction_checks=False
    )

    with pytest.raises(ValidationError):
        _write_buffer({"lcs": lcs})

    # orientations have wrong shape -----------------------
    orientation = xr.DataArray(
        data=[[1, 2], [3, 4]], dims=["c", "v"], coords={"c": ["x", "y"], "v": [0, 1]},
    )
    coordinates = xr.DataArray(
        data=[1, 2, 3], dims=["u"], coords={"u": ["x", "y", "z"]},
    )
    lcs = tf.LocalCoordinateSystem(
        orientation=orientation, coordinates=coordinates, construction_checks=False
    )

    with pytest.raises(ValidationError):
        _write_buffer({"lcs": lcs})


# weldx.transformations.CoordinateSystemManager ----------------------------------------
def get_example_coordinate_system_manager():
    """Get a consistent CoordinateSystemManager instance for test purposes."""
    csm = tf.CoordinateSystemManager("root")
    csm.create_cs("lcs_01", "root", coordinates=[1, 2, 3])
    csm.create_cs(
        "lcs_02",
        "root",
        orientation=tf.rotation_matrix_z(np.pi / 3),
        coordinates=[4, -7, 8],
    )
    csm.create_cs(
        "lcs_03",
        "lcs_02",
        orientation=tf.rotation_matrix_y(np.pi / 11),
        coordinates=[4, -7, 8],
    )
    return csm


@pytest.mark.parametrize("copy_arrays", [True, False])
@pytest.mark.parametrize("lazy_load", [True, False])
def test_coordinate_system_manager(copy_arrays, lazy_load):
    csm = get_example_coordinate_system_manager()
    tree = {"cs_hierarchy": csm}
    data = _write_read_buffer(
        tree, open_kwargs={"copy_arrays": copy_arrays, "lazy_load": lazy_load}
    )
    csm_file = data["cs_hierarchy"]
    assert csm == csm_file


# --------------------------------------------------------------------------------------
# TimeSeries
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize("copy_arrays", [True, False])
@pytest.mark.parametrize("lazy_load", [True, False])
@pytest.mark.parametrize(
    "ts",
    [
        TimeSeries(Q_(42, "m")),
        TimeSeries(Q_([42, 23, 12], "m"), time=pd.TimedeltaIndex([0, 2, 4])),
        TimeSeries(Q_([42, 23, 12], "m"), time=pd.TimedeltaIndex([0, 2, 5])),
        TimeSeries(ME("a*t+b", parameters={"a": Q_(2, "1/s"), "b": Q_(5, "")})),
    ],
)
def test_time_series_discrete(ts, copy_arrays, lazy_load):
    ts_file = _write_read_buffer(
        {"ts": ts}, open_kwargs={"copy_arrays": copy_arrays, "lazy_load": lazy_load}
    )["ts"]
    if isinstance(ts.data, ME):
        assert ts.data == ts_file.data
    else:
        assert np.all(ts_file.data == ts.data)
    assert np.all(ts_file.time == ts.time)
    assert ts_file.interpolation == ts.interpolation