#!/usr/bin/env python

from haversine import haversine, Unit
from lxml import etree
import argparse
import logging
import os
import sys

DEFAULT_NAMESPACE = 'http://www.topografix.com/GPX/1/1'


class GpxFile:
    def __init__(self, xml_filepath, min_distance, max_points_per_file, output_directory, output_file_count):
        self.xml_filepath        = xml_filepath
        self.min_distance        = min_distance
        self.max_points_per_file = max_points_per_file
        self.output_directory    = output_directory
        self.output_file_count   = output_file_count

        self.xml_filename = os.path.basename(self.xml_filepath)

        self._setup_logger()

    def process_file(self):
        self.tree = etree.parse(self.xml_filepath)

        reduced_trackpoints = self._reduce_close_trackpoints()

        max_points = int(self.max_points_per_file) * int(self.output_file_count)
        reduced_trackpoints = self._reduce_to_max_number_of_points(reduced_trackpoints, max_points)

        waypoints = self._translate_trackpoints_to_waypoints(reduced_trackpoints)

        self._write_waypoints_to_n_files(
            waypoints,
            output_directory=self.output_directory,
            max_number_of_points_per_file=self.max_points_per_file,
            max_number_of_output_files=self.output_file_count
        )

    def _route_name(self):
        return self.tree.find('.//{{{}}}name'.format(DEFAULT_NAMESPACE)).text or 'Unnamed'

    def _waypoint_root(self, route_name, index, total_count, route_bounds):
        root = etree.Element('gpx',
            version="1.1",
            xmlns=DEFAULT_NAMESPACE,
            creator='GPX Split'
        )

        metadata = etree.SubElement(root, 'metadata')
        if route_bounds:
           metadata.append(etree.Element('bounds',
                                        minlat=route_bounds['minlat'],
                                        minlon=route_bounds['minlon'],
                                        maxlat=route_bounds['maxlat'],
                                        maxlon=route_bounds['maxlon'],
                                    )
                            )

        route = etree.Element('rte')
        if route_name:
            name_element = etree.Element('name')
            name_element.text = '{}/{} - {}'.format(index, total_count, route_name)
            route.append(name_element)
        root.append(route)

        return root

    def _reduce_close_trackpoints(self):
        original_trackpoints = self._load_trackpoints()

        reduced_trackpoints = [original_trackpoints[0]]

        for trackpoint in original_trackpoints:
            distance = haversine(
                (float(reduced_trackpoints[-1].attrib['lat']), float(reduced_trackpoints[-1].attrib['lon'])),
                (float(trackpoint.attrib['lat']), float(trackpoint.attrib['lon'])),
                unit=Unit.METERS
            )

            if distance >= self.min_distance:
                reduced_trackpoints.append(trackpoint)

        logging.info("reduced to {} points".format(len(reduced_trackpoints)))

        return reduced_trackpoints

    def _load_trackpoints(self):
        trackpoints = self.tree.findall('.//{{{}}}trkpt'.format(DEFAULT_NAMESPACE))
        logging.info("loaded {} points".format(len(trackpoints)))
        return trackpoints

    def _reduce_to_max_number_of_points(self, trackpoints, max_points):
        if len(trackpoints) <= max_points:
            return trackpoints

        include_ratio = len(trackpoints) / max_points

        reduced_trackpoints = []
        for count, trackpoint in enumerate(trackpoints, start=1):
            if count % include_ratio < 1:
                reduced_trackpoints.append(trackpoint)

        logging.info("reduced to {} points".format(len(reduced_trackpoints)))
        return reduced_trackpoints

    def _bounds_from_waypoints(self, waypoints):
        minlat, minlon, maxlat, maxlon = None, None, None, None
        for waypoint in waypoints:
            if minlat is None or float(waypoint.attrib['lat']) < minlat:
                minlat = float(waypoint.attrib['lat'])
            if maxlat is None or float(waypoint.attrib['lat']) > maxlat:
                maxlat = float(waypoint.attrib['lat'])
            if minlon is None or float(waypoint.attrib['lon']) < minlon:
                minlon = float(waypoint.attrib['lon'])
            if maxlon is None or float(waypoint.attrib['lon']) > maxlon:
                maxlon = float(waypoint.attrib['lon'])
        return {'minlat': str(minlat), 'minlon': str(minlon), 'maxlat': str(maxlat), 'maxlon': str(maxlon)}

    def _write_waypoints_to_n_files(self, waypoints, output_directory, max_number_of_points_per_file, max_number_of_output_files):
        if len(waypoints) > max_number_of_points_per_file * max_number_of_output_files:
            logging.error(
                "Directed to write {} points to {} files, with {} points-per-file. This is unpossible"
                .format(len(waypoints), max_number_of_output_files, max_number_of_points_per_file)
            )

        route_name = self._route_name()
        chunked_points = list(self._chunk_list(waypoints, max_number_of_points_per_file))
        file_basename, file_extension = os.path.splitext(self.xml_filename)

        for count, chunk in enumerate(chunked_points, start=1):
            logging.info("Writing {}/{} files".format(count, len(chunked_points)))

            output_tree = self._waypoint_root(
                route_name=route_name,
                index=count,
                total_count=len(chunked_points),
                route_bounds=self._bounds_from_waypoints(chunk)
            )
            route = output_tree.find('.//rte'.format(DEFAULT_NAMESPACE))

            for point in chunk:
                route.append(point)

            self._write_tree_to_file(
                os.path.join(
                    output_directory,
                    '{}_-_{}{}'.format(count, file_basename, file_extension)
                ),
                output_tree
            )

    def _translate_trackpoints_to_waypoints(self, trackpoints):
        return list(map(
            lambda point: etree.Element('rtept', lat=point.attrib['lat'], lon=point.attrib['lon']),
            trackpoints
        ))


    def _write_tree_to_file(self, filename, tree):
        root = etree.ElementTree(tree)
        root.write(filename, pretty_print=True)

    @classmethod
    def _chunk_list(cls, array, n):
        for i in range(0, len(array), n):
            yield array[i:i + n]

    def _setup_logger(self):
        root = logging.getLogger()
        root.setLevel(logging.DEBUG)

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        root.addHandler(handler)


def parse_args():
    parser = argparse.ArgumentParser(description="Split GPX tracks")
    parser.add_argument('-p', '--points', default=250, type=int, help='Points per file. Defaults to 250')
    parser.add_argument('-f', '--output-file-count', default=10, type=int, help='Max number of output files. Defaults to 10.')
    parser.add_argument('-d', '--min-distance', type=float, default=10, help='Remove points less than minimum distance. Defaults to 10 meters.')
    parser.add_argument('-o', '--output-directory', help='')
    parser.add_argument('xml_file')

    args = parser.parse_args()

    if not args.output_directory:
        args.output_directory = os.path.dirname(args.xml_file)

    return args


def main():
    args = parse_args()

    gpx_file = GpxFile(
        xml_filepath=args.xml_file,
        min_distance=args.min_distance,
        max_points_per_file=args.points,
        output_directory=args.output_directory,
        output_file_count=args.output_file_count
    )

    gpx_file.process_file()


if __name__ == "__main__":
    main()
