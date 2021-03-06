from collections.abc import Sequence
import os
from pathlib import Path
import re
import urllib.request
from urllib.request import Request


class URLFix(object):
    def __init__(self, input_file, output_file=None):
        """
        :param input_file: Path to input_file
        :param output_file: Path to output_file
        """
        self.input_file = input_file
        self.output_file = output_file
        # automatically detect input file format
        format_pattern = r'.+\.(\w+)'
        matches = re.findall(format_pattern, self.input_file)
        self.input_format = matches[0] if len(matches) > 0 else ''

    def __compare_file_content(self, tmp_file):
        """
        :param temp_file. temporary file name containing original file contents
        :return  Compares the content of original file with temp file line by line and returns a bool value
        True - If content is matched, False otherwise
        """
        content_matched = False
        with open(self.input_file, "r") as f1, open(tmp_file, "r") as f2:
            for content_orig, content_temp in zip(f1, f2):
                if content_orig != content_temp:
                    print(f"Content did not matched between {self.input_file} and {tmp_file}")
                    print(content_orig, content_temp)
                    break
                else:
                    content_matched = True
        return content_matched

    def replace_urls(self, verbose=False, correct_urls=None, inplace=False):
        """
        :param verbose Logical. Should you be notified of what URLs have moved? Defaults to False.
        :param correct_urls. A sequence of urls known to be correct.
        :param inplace. Flag for inplace update operation.
        :return  Replaces outdated URL and writes to the specified file. It also returns the number of URLs that have
        changed. The latter is useful for tests.
        """
        if self.input_format not in ("md", "txt"):
            raise NotImplementedError(f"File format {self.input_format} is not yet supported.")
        else:
            pass

        link_text = "[^]]+"
        # Better markdown link matching  taken from https://stackoverflow.com/a/23395483/10323798
        # http:// or https:// followed by anything but a closing paren
        actual_link = "http[s]?://[^)]+"
        combined_regex = f"\[({link_text})]\(\s*({actual_link})\s*\)"
        # Match only links in a text file, do not text that follows.
        # Assumes that links will always be followed by a space.
        final_regex = "http[s]?://[^\s]+" if self.input_format == "txt" else combined_regex

        number_moved = 0
        number_of_urls = 0
        remove_orig_file = False

        if not self.output_file and not inplace:
            raise ValueError("Please provide an output file to write to.")
        output_file = self.output_file
        if inplace:
            output_file = "replacements_tmp.txt"
            with open(output_file, "w"):
                #Create temp file if temp file is not specified
                pass

        if not all(os.path.isfile(x) for x in [self.input_file, output_file]):
            raise FileNotFoundError("input_file and output_file should be valid files.")

        with open(self.input_file, "r") as input_f, open(output_file, "w") as out_f:

            for line in input_f:
                matched_url = re.findall(final_regex, line)

                if len(matched_url) != 0:
                    matched_url = matched_url[0][1] if self.input_format == "md" else matched_url[0]
                    number_of_urls += 1

                    # make sure 'correct_urls' parameter is a sequence

                    if isinstance(correct_urls, Sequence) and matched_url in correct_urls:
                        # skip current url if it's in 'correct_urls'
                        print(f'{matched_url} is already valid.')
                        continue

                    # This printing step while unnecessary may be useful to make sure things work as expected
                    if verbose:
                        print(f"Found {matched_url} in {input_f.name}, now validating.. ")
                    visited_url = urllib.request.urlopen(Request(matched_url, headers={'User-Agent': 'XYZ/3.0'}))
                    url_used = visited_url.geturl()
                    if url_used != matched_url:
                        number_moved += 1
                        if verbose:
                            print(f"{matched_url} replaced with {url_used} in {out_f.name}")
                    out_f.write(line.replace(matched_url, url_used))

        if inplace:
            remove_orig_file = self.__compare_file_content(output_file)
            if remove_orig_file:
                os.remove(self.input_file)
                if verbose:
                    print(f"{self.input_file} removed successfully")
                os.rename(output_file, self.input_file)
                if verbose:
                    print(f"{output_file} renamed with {self.input_file} successfully")
        information = "URLs have changed" if number_moved != 1 else "URL has changed"
        print(f"{number_moved} {information} of the {number_of_urls} links found in {self.input_file}")
        return number_moved


class DirURLFix(object):
    def __init__(self, input_dir):
        """
        :param input_dir: Path to input_dir.
        """
        self.input_dir = input_dir
        self.use_files = Path(self.input_dir)

    def __replace_by_format(self, _format, **kwargs):
        """
        :param _format: Input format of the files. Currently supports md and txt
        :param inplace: Flag for inplace update operation.
        :return: File with outdated URLs replaced.
        """
        for input_file in self.use_files.glob(f'*.{_format}'):
            input_file = str(input_file) # convert object to path string
            if "inplace" in kwargs and kwargs["inplace"]:
                output_file = "replacements_tmp.txt"
            else:
                if '_output' in input_file:
                    print(f"File is a fix of another file: {input_file}")
                    continue  # skip output files

                output_file = input_file.replace(f'.{_format}', f'_output.{_format}')
                if os.path.exists(output_file):
                    print(f"File already fixed: {input_file}")
                    continue  # skip file that's already been fixed

                with open(output_file, 'w'):
                    pass  # create an empty output file
            return URLFix(input_file, output_file).replace_urls(**kwargs)

    def replace_urls(self, **kwargs):
        if not os.path.exists(self.input_dir):
            raise OSError('Path does not exist!')
        if not os.path.isdir(self.input_dir):
            raise NotADirectoryError('Input path must be a directory!')
        number_moved = []
        for _format in ('md', 'txt'):
            for file_found in list(self.use_files.glob(f"*.{_format}")):
                number_moved.append(self.__replace_by_format(_format, **kwargs))

        print('All files have been updated, thank you for using urlfix.')
        return number_moved
