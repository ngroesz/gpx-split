#!/usr/bin/env python3

import argparse
import math
import xml.etree.ElementTree as ET
import os
from haversine import haversine, Unit

DEFAULT_NAMESPACE = 'http://www.topografix.com/GPX/1/1'

class GpxFile:
    def __init__(self, xml_filepath):
        self.tree = ET.parse(xml_filepath)
        self.root = self.tree.getroot()

        self.namespaces = dict([
            node for _, node in ET.iterparse(
                xml_filepath , events=['start-ns']
            )
        ])

        self.xml_file_basename = os.path.basename(xml_filepath)

    def reduce_close_track_points(self, min_distance=10):
        original_track_points = self.load_track_points()

        reduced_track_points = [original_track_points[0]]

        for track_point in original_track_points:
            distance = haversine(
                (float(reduced_track_points[-1].attrib['lat']), float(reduced_track_points[-1].attrib['lon'])),
                (float(track_point.attrib['lat']), float(track_point.attrib['lon'])),
                unit=Unit.METERS
            )

            if distance >= min_distance:
                reduced_track_points.append(track_point)

        print("reduced to {} points".format(len(reduced_track_points)))

        return reduced_track_points

    def load_track_points(self):
        track_points = self.tree.findall('.//{{{}}}trkpt'.format(DEFAULT_NAMESPACE))
        print("loaded {} points".format(len(track_points)))
        return track_points

    def reduce_to_max_number_of_points(self, track_points, max_points):
        if len(track_points) <= max_points:
            return track_points

        include_ratio = len(track_points) / max_points

        reduced_track_points = []
        for count, track_point in enumerate(track_points, start=1):
            if count % include_ratio < 1:
                reduced_track_points.append(track_point)

        print("reduced to {} points".format(len(reduced_track_points)))
        return reduced_track_points

    def write_track_points_to_n_files(self, track_points, number_of_files):
        

    # https://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks
    def chunks(lst, n):
        """Yield successive n-sized chunks from lst."""
        for i in range(0, len(lst), n):
            yield lst[i:i + n]
def main():
    parser = argparse.ArgumentParser(description="Split GPX tracks")
    parser.add_argument('-p', '--points', default=250, help='Points per file. Defaults to 250')
    parser.add_argument('-f', '--files', default=10, help='Max number of files. Defaults to 10.')
    parser.add_argument('-d', '--min-distance', type=float, default=10, help='Remove points less than minimum distance. Defaults to 10 meters.')
    parser.add_argument('xml_file')

    args = parser.parse_args()

    print(args)
    gpx_file = GpxFile(args.xml_file)

    reduced_track_points = gpx_file.reduce_close_track_points(min_distance=args.min_distance)
    reduced_track_points = gpx_file.reduce_to_max_number_of_points(reduced_track_points, args.points * args.files)
    gpx_file.write_track_points_to_n_files(track_points, number_of_files=args.files)
    
    
if __name__ == "__main__":
    main()
