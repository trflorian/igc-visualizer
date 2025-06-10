import argparse
import logging

import numpy as np
import rerun as rr

from igc import IGCParser

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the IGC Visualizer with Rerun.")
    parser.add_argument("igc_path", type=str, help="Path to the IGC file to visualize.")
    args = parser.parse_args()

    parser = IGCParser(args.igc_path)

    df = parser.to_pandas()

    logger.info(df.head())
    #                 timestamp    latitude   longitude  av_flag  pressure_altitude  gps_altitude
    # 0 2025-05-10 09:55:32  885.083333  422.433333     True                0.0        1909.0
    # 1 2025-05-10 09:55:33  884.983333  422.316667     True                0.0        1908.0
    # 2 2025-05-10 09:55:34  884.916667  422.266667     True                0.0        1908.0
    # 3 2025-05-10 09:55:35  884.850000  422.250000     True                0.0        1906.0
    # 4 2025-05-10 09:55:36  884.766667  422.250000     True                0.0        1905.0

    # Initialize Rerun with the provided IGC file
    rr.init("igc_visualizer", spawn=True)

    # Log the DataFrame to Rerun
    # rr.log(
    #     "igc_data",
    #     rr.GeoPoints(
    #         lat_lon=df[["latitude", "longitude"]].values,
    #     ),
    # )

    # Earth’s mean radius in meters
    R = 6_371_000.0

    # reference point (first row)
    lat0 = df.loc[0, "latitude"]
    lon0 = df.loc[0, "longitude"]
    alt0 = df.loc[0, "gps_altitude"]

    logger.info(f"Reference point: lat={lat0}, lon={lon0}, alt={alt0}")
    # log max, min, and mean altitude
    logger.info(f"Max altitude: {df['gps_altitude'].max()} m")
    logger.info(f"Min altitude: {df['gps_altitude'].min()} m")
    logger.info(f"Mean altitude: {df['gps_altitude'].mean()} m")

    # convert differences to radians
    dlat = np.deg2rad(df["latitude"] - lat0)
    dlon = np.deg2rad(df["longitude"] - lon0)
    lat0_rad = np.deg2rad(lat0)

    # compute local Cartesian offsets
    df["dx"] = R * dlon * np.cos(lat0_rad)  # East–West offset (m)
    df["dy"] = R * dlat  # North–South offset (m)
    df["dz"] = (df["gps_altitude"] - alt0) * 1000  # Vertical offset (m)

    df["velocity"] = np.sqrt(df["dx"] ** 2 + df["dy"] ** 2 + df["dz"] ** 2)
    df["velocity_smooth"] = df["velocity"].rolling(window=10, min_periods=1).mean()

    df["velocity_smooth_norm"] = np.linalg.norm(df["velocity_smooth"].values)

    # print max, min, and mean velocity
    logger.info(f"Max velocity: {df['velocity_smooth'].max()} m/s")
    logger.info(f"Min velocity: {df['velocity_smooth'].min()} m/s")
    logger.info(f"Mean velocity: {df['velocity_smooth'].mean()} m/s")

    rr.log(
        "igc_data",
        rr.LineStrips3D(
            strips=df[["dx", "dy", "dz"]].values / 1000.0,  # Convert to kilometers
            radii=5.0,
            colors=df["velocity"],
        ),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
