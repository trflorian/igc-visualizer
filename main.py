import argparse
import logging

import rerun as rr

from igc import IGCParser


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the IGC Visualizer with Rerun.")
    parser.add_argument("igc_path", type=str, help="Path to the IGC file to visualize.")
    args = parser.parse_args()

    parser = IGCParser(args.igc_path)

    # Initialize Rerun with the provided IGC file
    # rr.init("igc_visualizer", spawn=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
