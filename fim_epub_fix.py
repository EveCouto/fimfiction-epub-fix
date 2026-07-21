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


def dir_path(string: str):
    """Checks if string is a dir path

    Args:
        string (str): input string

    Raises:
        NotADirectoryError: error

    Returns:
        str: returns the absolute path
    """
    if os.path.isdir(string):
        return os.path.abspath(string)
    else:
        raise NotADirectoryError(string)


def is_epub(path: str) -> bool:
    if not os.path.isfile():
        return False
    if os.path.splitext()[1] != ".epub":
        return False
    return True


def get_files(dir_path: str, files: list[str] = []) -> list[str]:
    abs_path = os.path.abspath(dir_path)
    for item in os.listdir(abs_path):
        item_path = os.path.join(abs_path, item)
        if os.path.isdir(item_path):
            files.append(get_files(item_path, files))
        elif os.path.isfile(item_path):
            files.append(item_path)
    return files


def start_parser():
    """Creates a argument processor

    Returns:
        Namespace: Returns the args
    """
    parser = argparse.ArgumentParser(description=(
        "Adds images to epubs using urls"))
    parser.add_argument("-i", "--input",
                        help="input path or file",
                        required=True,
                        type=(dir_path or file_path),
                        nargs="+")
    parser.add_argument("-lv", "--less_verbose",
                        help="less info",
                        action="store_false")
    parser.add_argument("-ov", "--overwrite",
                        help="Ignores output and overwrites",
                        action="store_true")
    parser.add_argument("-r", "--recurse",
                        help="Goes through all subfolders",
                        action="store_true")
    args = parser.parse_args()
    return args


# TODO add recursive folder search.
def main():
    # Gets args and sets them to local variables
    args = start_parser()
    paths = args.input

    verbose = args.verbose
    recurse = args.recurse

    files = []
    for path in paths:
        if recurse:
            if os.path.isdir(path):
                files += get_files(path)
            else:
                print(f"**Recurse set, file: {path} ignored**")
        else:
            if os.path.isfile(path):
                files.append(path)
            else:
                print(f"**Recurse not set, dir: {path} ignored**")
            pass

    epubs = []
    for file in files:
        if is_epub(file):
            epubs.append(file)
        else:
            print(f"**{file} is not an epub, skipping**")

    print("---------------------")
    # Runs the main code
    for epub in epubs:

        # Print starting
        print(f"Fixing '{os.path.basename(epub)}'")

        out_file = os.path.splitext(epub)[0] + "-fixed.epub"
        update_zip(epub, out_file, scan_zip(epub, ".html"), verbose)

        if args.overwrite:
            os.replace(out_file, epub)

        # Prints Complete
        print(f"\033[92mFixing '{os.path.basename(epub)}' Complete!\033[0m")
        if args.overwrite:
            print(f"Located at {epub}")
        else:
            print(f"Located at {out_file}")
        print("---------------------")


if __name__ == "__main__":
    main()
