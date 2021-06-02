#!/usr/bin/env python

from haversine import haversine, Unit
from lxml import etree
import argparse
import copy
import logging
import os
import sys

DEFAULT_NAMESPACE = 'http://www.topografix.com/GPX/1/1'


class GpxFile:
    def __init__(self, xml_filepath):
        self.tree = etree.parse(xml_filepath)

        self.xml_filename = os.path.basename(xml_filepath)

        self.empty_tree = self.tree_without_track_points()

    def tree_without_track_points(self):
        new_tree = copy.deepcopy(self.tree)

        points = new_tree.findall('.//{{{}}}trkpt'.format(DEFAULT_NAMESPACE))
        for point in points:
            point.getparent().remove(point)

        segments = new_tree.findall('.//{{{}}}trkseg'.format(DEFAULT_NAMESPACE))
        for segment in segments[1:-1]:
            segment.getparent().remove(segment)

        return new_tree

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

    def write_track_points_to_n_files(self, track_points, output_directory, max_number_of_points_per_file, max_number_of_files):
        if len(track_points) > max_number_of_points_per_file * max_number_of_files:
            logging.error(
                "Directed to write {} points to {} files, with {} points-per-file. This is unpossible"
                .format(len(track_points), max_number_of_files, max_number_of_points_per_file)
            )

        chunked_points = list(self.chunk_list(track_points, max_number_of_points_per_file))

        logging.info("Writing {} files".format(len(chunked_points)))

        file_basename, file_extension = os.path.splitext(self.xml_filename)

        for count, chunk in enumerate(chunked_points, start=1):
            logging.info("Writing {}/{} files".format(count, len(chunked_points)))
            tree = self.tree_with_new_points(chunk)

            self.write_tree_to_file(
                '{}_-_{}{}'.format(
                    os.path.join(output_directory, file_basename),
                    count,
                    file_extension),
                tree
            )

    def tree_with_new_points(self, track_points):
        new_tree = copy.deepcopy(self.empty_tree)
        segment = new_tree.find('.//{{{}}}trkseg'.format(DEFAULT_NAMESPACE))
        for track_point in track_points:
            segment.append(track_point)

        return new_tree

    def write_tree_to_file(self, filename, tree):
        tree.write(filename, pretty_print=True)

    # https://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks
    @classmethod
    def chunk_list(cls, array, n):
        for i in range(0, len(array), n):
            yield array[i:i + n]


def setup_logger():
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    root.addHandler(handler)


def parse_args():
    parser = argparse.ArgumentParser(description="Split GPX tracks")
    parser.add_argument('-p', '--points', default=250, type=int, help='Points per file. Defaults to 250')
    parser.add_argument('-f', '--files', default=10, type=int, help='Max number of files. Defaults to 10.')
    parser.add_argument('-d', '--min-distance', type=float, default=10, help='Remove points less than minimum distance. Defaults to 10 meters.')
    parser.add_argument('-o', '--output-directory', help='')
    parser.add_argument('xml_file')

    args = parser.parse_args()

    if not args.output_directory:
        args.output_directory = os.path.dirname(args.xml_file)
        print('not {}'.format(args.output_directory))

    return args


def process_file(args):
    gpx_file = GpxFile(args.xml_file)

    reduced_track_points = gpx_file.reduce_close_track_points(min_distance=args.min_distance)

    max_points = int(args.points) * int(args.files)
    reduced_track_points = gpx_file.reduce_to_max_number_of_points(reduced_track_points, max_points)

    gpx_file.write_track_points_to_n_files(
        reduced_track_points,
        output_directory=args.output_directory,
        max_number_of_points_per_file=args.points,
        max_number_of_files=args.files
    )


def main():
    setup_logger()
    args = parse_args()
    process_file(args)


if __name__ == "__main__":
    main()
