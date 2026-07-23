import os
import argparse
import zipfile


def scan_epub(zip_path: str) -> list[str]:
    # Open zip, read files
    with zipfile.ZipFile(zip_path) as zip:
        return zip.namelist()


def merge_epub(path1: str, path2: str):
    pass


def is_epub(path: str) -> bool:
    if not os.path.isfile(path):
        return False
    if os.path.splitext(path)[1] != ".epub":
        return False
    return True


def start_parser():
    """Creates a argument processor

    Returns:
        Namespace: Returns the args
    """
    parser = argparse.ArgumentParser(description=(
        "Merges two epubs"))
    parser.add_argument("-i", "--input",
                        help="input files",
                        required=True,
                        nargs=2)
    parser.add_argument("-o", "--output",
                        help="output directory")
    parser.add_argument("-ov", "--overwrite",
                        help="overwrites first file",
                        action="store_true")
    parser.add_argument("-d", "--delete",
                        help="will delete second file",
                        action="store_true")
    parser.add_argument("-y", "--skip_confirm",
                        help="skips confirmations",
                        action="store_true")
    args = parser.parse_args()
    return args


def main():
    args = start_parser()
    temp_path = r"./temp/temp.epub"

    # Checks files to ensure epub and converts to abspath
    # args.input[0] is path1, [1] is path2
    for i in range(len(args.input)):
        if is_epub(args.input[i]):
            args.input[i] = os.path.abspath(args.input[i])
        else:
            print(f"\033[91m** File: '{args.input[i]}' " +
                  "is not an epub, aborting.**\033[0m")
            quit()

    if args.delete and not args.skip_confirm:
        while True:
            ans = input(f"This is about remove '{args.input[1]}'," +
                        " do you want to proceed? (Y/n) ").lower()
            if ans == "y":
                print("Confirmed, continuing.")
                print("=====================")
                break
            elif ans == "n":
                print("\033[91mAborting, no files changed.\033[0m")
                quit()
            else:
                print("Please try again.")

    if args.overwrite and not args.skip_confirm:
        while True:
            ans = input(f"This is about to overwrite '{args.input[0]}'," +
                        " do you want to proceed? (Y/n) ").lower()
            if ans == "y":
                print("Confirmed, continuing.")
                print("=====================")
                break
            elif ans == "n":
                print("\033[91mAborting, no files changed.\033[0m")
                quit()
            else:
                print("Please try again.")

    print(args.input)
    print(scan_epub(args.input[0]))
    # TODO all the main code!!

    # overwrites first file
    if args.overwrite:
        os.replace(temp_path, args.input[0])

    # deletes second file
    if args.delete:
        os.remove(args.input[1])


if __name__ == "__main__":
    main()
