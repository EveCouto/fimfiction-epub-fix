import os
import zipfile
import re
import urllib.parse
import urllib.request
import argparse


def scan_zip(zip_path: str, file_ext: str,
             pattern: str = r"(<img src=\"http[^>]*\/>)", ) -> dict:
    """Scans zip file for pattern matches in files

    Args:
        zip_path (str): filepath of zip
        pattern (str): regex pattern, defaults
        file_ext (str): file extension

    Returns:
        dict: filename -> match(es)
    """

    loc_to_match = {}

    if not zipfile.is_zipfile(zip_path):
        print("File was not a zip, skipping")
        return 0

    # Open zip, read files and gets instances of pattern
    with zipfile.ZipFile(zip_path) as zip:
        for zip_info in zip.infolist():
            if file_ext in zip_info.filename:
                with zip.open(zip_info) as in_file:
                    content = in_file.read().decode()
                    matches = re.findall(pattern, content)
                    if matches:
                        loc_to_match[zip_info.filename] = matches
    return loc_to_match


def hidden_link_fix(link: str, pattern: str = r'url=(.*?)(?=%3F|")') -> str:
    """checks string and extracts hidden url

    Args:
        link (str): a string containing a hidden link
        pattern (str): regex pattern. Optional. Defaults to r"url=(.*)\"".

    Returns:
        str: fixed link or original if no changes
    """

    # Checks for matches in link
    matches = re.search(pattern, link)

    # Returns unquoted version if a match
    if matches:
        return urllib.parse.unquote(matches.group(1))
    else:
        print("no matches in link, returning original")
        if link.find("?"):
            return link[link.find("http"):link.find("?")]
        else:
            return link[link.find("http"):link.find('"')]


def get_img_data(img: str) -> dict:
    """Takes string and gets more info out of it

    Args:
        img (str): string representing an img url

    Returns:
        dict: contains all the img info
    """

    img_link = hidden_link_fix(img)
    img_name = os.path.basename(img_link)
    new_src = f'<img src="images/{img_name}"/>'

    return {"orig": img, "link": img_link,
            "name": img_name, "src": new_src}


def replace_patterns(content, old, new) -> str:
    pass


def update_xml(xml: str, links: set):
    """Updates XML, only really works with byte

    Args:
        xml (str): xml text
        links (set): links used in update

    Returns:
        byte: xml text output
    """

    upper = xml[:xml.find(bytes("</manifest>", "cp437"))]
    lower = xml[xml.find(bytes("</manifest>", "cp437")):]

    for link in links:
        name = os.path.basename(link)
        if bytes(name, "cp437") not in xml:

            if os.path.splitext(name)[1] == "jpeg":
                print(os.path.splitext(name)[1])
                media = "jpeg"
            else:
                media = os.path.splitext(name)[1]
            add = (f'\t\t<item id="{name}" ' +
                   f'href="images/{name}" ' +
                   f'media-type="image/{media}" />\n')
            upper += bytes(add, "cp437")

    return upper + lower


def update_zip(in_zip_path: str, out_zip_path: str,
               file_to_img: dict[str, list[str]], verbose: bool) -> None:
    """Takes input and output and data to update epub zip

    Args:
        in_zip_path (str): input filepath
        out_zip_path (str): output filepath
        file_to_img (dict[str, list[str]]): data dict
        verbose (bool): determines console prints
    """

    print("---------------------")
    print(f"Fixing '{os.path.basename(in_zip_path)}'")

    # Updates data in dictionary
    for key in file_to_img.keys():
        file_to_img[key] = list(map(get_img_data, file_to_img[key]))

    # Gets all links into a set to prevent duplicates
    links = set()
    for key in file_to_img.keys():
        for img in file_to_img[key]:
            links.add(img["link"])

    # Opens input and output zip files.
    with (zipfile.ZipFile(in_zip_path) as in_zip,
          zipfile.ZipFile(out_zip_path, 'w') as out_zip):
        for in_zip_info in in_zip.infolist():
            with in_zip.open(in_zip_info) as in_file:
                content = in_file.read()

            # Runs through all documents needing editing and updates
            if in_zip_info.filename in file_to_img.keys():
                for img in file_to_img[in_zip_info.filename]:
                    content = content.replace(bytes(img["orig"], "cp437"),
                                              bytes(img["src"], "cp437"))

            # Runs through the opf data file
            if ".opf" in in_zip_info.filename:
                content = update_xml(content, links)
            out_zip.writestr(in_zip_info.filename, content)

        # Checks if image is already in zip, downloads new
        for link in links:
            name = os.path.basename(link)
            if name not in in_zip.namelist():
                if verbose:
                    print("Downloading: " + link)
                try:
                    file = urllib.request.urlopen(link).read()
                except urllib.error.HTTPError:
                    print(f"HTTP Error, skipping image {link}")
                out_zip.writestr(f"{"images/"+name}", file)

    print(f"\033[92mFixing '{os.path.basename(in_zip_path)}' Complete!\033[0m")
    print(f"Located at {out_zip_path}")
    print("---------------------")


def file_path(string: str):
    """Checks if string is a file path

    Args:
        string (str): input string

    Raises:
        NotADirectoryError: error

    Returns:
        str: returns the absolute path
    """
    if os.path.isfile(string):
        return os.path.abspath(string)
    else:
        raise NotADirectoryError(string)


def start_parser():
    """Creates a argument processor

    Returns:
        Namespace: Returns the args
    """
    parser = argparse.ArgumentParser(description=(
        "Adds images to epubs using urls"))
    parser.add_argument("-i", "--input",
                        help="input path",
                        required=True,
                        type=file_path)
    parser.add_argument("-o", "--output",
                        help="Output  path",
                        type=file_path)
    parser.add_argument("-v", "--verbose",
                        help="more info",
                        type=bool,
                        default=True)
    args = parser.parse_args()
    return args


def main():
    # Gets args and sets them to local variables
    args = start_parser()
    in_file = args.input
    if not args.output:
        print("rans")
        out_file = os.path.splitext(args.input)[0] + "-fixed.epub"
        print(out_file)
    else:
        out_file = args.output
    verbose = args.verbose

    # Runs the main code
    update_zip(in_file, out_file, scan_zip(in_file, ".html"), verbose)


if __name__ == "__main__":
    main()
