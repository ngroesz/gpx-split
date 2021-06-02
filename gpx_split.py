import argparse
from bs4 import BeautifulSoup

def gpx_split(xml_file):
    with open(xml_file, 'r') as fp:
        xml = fp.read()

    filter_track_points(xml)

def filter_track_points(xml)
    track_points = original_track_points(xml)

    print("count: {}".format(len(track_points)))

    track_points = [track_points[0], track_points[1]]

def original_track_points(xml):
    tree = BeautifulSoup(xml, 'lxml')

    return tree.find_all('trkpt')
    #print(tree)
    #for track_point in tree.find_all('trkpt'):
    #    print('point: {}'.format(track_point))
    #
    #enumerate(track
    #print("file: {}".format(xml_file))
    #tree = ET.parse(xml_file)
    #root = tree.getroot()

    #print("root: {}".format(root.attrib))

    #my_namespaces = dict([
    #    node for _, node in ET.iterparse(
    #        xml_file, events=['start-ns']
    #    )
    #])

    #print("ns: {}".format(my_namespaces))

    ##for track_point in tree.findall('.//{http://www.topografix.com/GPX/1/1}trkpt'):
    #for track_point in tree.findall('.//{ns}trkpt', namespaces={'ns': 'http://www.topografix.com/GPX/1/1'}):
    #    print("point: {}".format(track_point))

def main():
    parser = argparse.ArgumentParser(description="Split GPX tracks")
    parser.add_argument('-p', '--points', default=250, help='Points per file. Defaults to 250')
    parser.add_argument('-f', '--files', default=10, help='Max number of files. Defaults to 10.')
    parser.add_argument('xml_file')

    args = parser.parse_args()

    gpx_split(args.xml_file)

if __name__ == "__main__":
    main()
