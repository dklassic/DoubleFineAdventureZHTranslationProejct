import os
import re
import argparse
from datetime import datetime
import sys

def parse_time(time_str):
    """
    Parses a time string from SRT format to a datetime object.
    Example: "00:01:15,123" -> datetime object
    """
    return datetime.strptime(time_str, "%H:%M:%S,%f")

def format_time(time_obj):
    """
    Formats a datetime object to SRT time string.
    Example: datetime object -> "00:01:15,123"
    """
    return time_obj.strftime("%H:%M:%S,%f")[:-3]

class Subtitle:
    def __init__(self, number, start, end, text):
        self.number = number  # int
        self.start = start    # datetime
        self.end = end        # datetime
        self.text = text      # list of strings

    def __str__(self):
        time_str = f"{format_time(self.start)} --> {format_time(self.end)}"
        text_str = "\n".join(self.text)
        return f"{self.number}\n{time_str}\n{text_str}\n"

def read_srt(file_path):
    """
    Reads an SRT file and returns a list of Subtitle objects.
    """
    subtitles = []
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    blocks = re.split(r'\n\s*\n', content.strip(), flags=re.MULTILINE)
    for block in blocks:
        lines = block.split('\n')
        if len(lines) >= 3:
            try:
                number = int(lines[0].strip())
            except ValueError:
                print(f"Warning: Subtitle number expected, got '{lines[0]}' in file '{file_path}'. Skipping block.")
                continue
            time_match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', lines[1].strip())
            if time_match:
                start_time = parse_time(time_match.group(1))
                end_time = parse_time(time_match.group(2))
                text = lines[2:]
                subtitles.append(Subtitle(number, start_time, end_time, text))
            else:
                print(f"Warning: Time format incorrect in block {number} of file '{file_path}'.")
    return subtitles

def write_srt(subtitles, file_path):
    """
    Writes a list of Subtitle objects to an SRT file.
    """
    with open(file_path, 'w', encoding='utf-8') as f:
        for subtitle in subtitles:
            f.write(str(subtitle))
            f.write('\n')  # SRT files separate blocks with a blank line

def trim_extra_spaces(subtitles):
    """
    Trims extra spaces from each line of subtitle text.
    - Removes leading and trailing spaces.
    - Replaces multiple consecutive spaces with a single space.
    - Optionally removes blank lines within subtitles.
    """
    for subtitle in subtitles:
        trimmed_text = []
        for line in subtitle.text:
            # Remove leading and trailing spaces
            line = line.strip()
            # Replace multiple spaces with a single space
            line = re.sub(r'\s+', ' ', line)
            if line:  # Avoid adding empty lines
                trimmed_text.append(line)
        subtitle.text = trimmed_text
    return subtitles

def merge_two_line_subtitles(subtitles):
    """
    Merges subtitles that have exactly two lines into one line.
    """
    for subtitle in subtitles:
        if len(subtitle.text) == 2:
            merged_text = ' '.join(subtitle.text)
            subtitle.text = [merged_text]
    return subtitles

def has_punctuation(text):
    """
    Checks if the text ends with a typical punctuation mark.
    """
    punctuation = {'.', '!', '?', '…', '。', '！', '？'}
    text = text.strip()
    if not text:
        return False
    return text[-1] in punctuation

def merge_subtitles_without_punctuation(subtitles):
    """
    Merges subtitles that end without punctuation with the next subtitle.
    Adjusts the timing accordingly.
    """
    merged_subtitles = []
    i = 0
    while i < len(subtitles):
        current = subtitles[i]
        # Check if current subtitle's last line ends with punctuation
        if has_punctuation(current.text[-1]):
            merged_subtitles.append(current)
            i += 1
        else:
            # Needs to merge with next subtitle if possible
            if i + 1 < len(subtitles):
                next_sub = subtitles[i + 1]
                # Merge current and next
                merged_text = ' '.join(current.text + next_sub.text)
                merged_start = current.start
                merged_end = next_sub.end
                merged_subtitle = Subtitle(
                    number=0,  # Temporary, will renumber later
                    start=merged_start,
                    end=merged_end,
                    text=[merged_text]
                )
                merged_subtitles.append(merged_subtitle)
                i += 2  # Skip the next subtitle as it's merged
            else:
                # Last subtitle without punctuation, cannot merge
                merged_subtitles.append(current)
                i += 1
    return merged_subtitles

def renumber_subtitles(subtitles):
    """
    Renumbers subtitles sequentially starting from 1.
    """
    for idx, subtitle in enumerate(subtitles, start=1):
        subtitle.number = idx
    return subtitles

def clean_subtitles(subtitles):
    """
    Performs all cleaning steps on the subtitles:
    1. Trims extra spaces.
    2. Merges two-line subtitles.
    3. Merges subtitles without proper punctuation.
    4. Renumbers subtitles.
    """
    subtitles = trim_extra_spaces(subtitles)
    subtitles = merge_two_line_subtitles(subtitles)
    subtitles = merge_subtitles_without_punctuation(subtitles)
    subtitles = renumber_subtitles(subtitles)
    return subtitles

def process_srt_file(input_path, output_path):
    """
    Processes a single SRT file: reads, cleans, and writes to a new file.
    """
    subtitles = read_srt(input_path)
    if not subtitles:
        print(f"No valid subtitles found in '{input_path}'. Skipping file.")
        return
    cleaned_subtitles = clean_subtitles(subtitles)
    write_srt(cleaned_subtitles, output_path)
    print(f"Processed '{os.path.basename(input_path)}' -> '{os.path.basename(output_path)}'")

def parse_arguments():
    """
    Parses command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Clean and preprocess SRT subtitle files.")
    parser.add_argument(
        '-p', '--path',
        type=str,
        required=True,
        help="Path to the main directory containing 'raw subtitles' folder."
    )
    parser.add_argument(
        '-i', '--input',
        type=str,
        default="raw subtitles",
        help="Name of the input subdirectory containing raw SRT files (default: 'raw subtitles')."
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default="preprocessed subtitles",
        help="Name of the output subdirectory to save cleaned SRT files (default: 'preprocessed subtitles')."
    )
    return parser.parse_args()

def main():
    args = parse_arguments()

    directory = args.path
    input_subdir = args.input
    output_subdir = args.output

    # Validate main directory
    if not os.path.isdir(directory):
        print(f"Error: The specified path '{directory}' is not a valid directory.")
        sys.exit(1)

    raw_subtitles_dir = os.path.join(directory, input_subdir)
    if not os.path.isdir(raw_subtitles_dir):
        print(f"Error: Input subdirectory '{input_subdir}' not found in '{directory}'.")
        sys.exit(1)

    preprocessed_subtitles_dir = os.path.join(directory, output_subdir)
    os.makedirs(preprocessed_subtitles_dir, exist_ok=True)

    # Find all .srt files in the input directory
    srt_files = [f for f in os.listdir(raw_subtitles_dir) if f.lower().endswith('.srt')]

    if not srt_files:
        print(f"No .srt files found in the '{input_subdir}' folder.")
        sys.exit(1)

    for srt_file in srt_files:
        input_file_path = os.path.join(raw_subtitles_dir, srt_file)
        base_name, ext = os.path.splitext(srt_file)
        output_file_name = f"{base_name}_cleaned{ext}"
        output_file_path = os.path.join(preprocessed_subtitles_dir, output_file_name)
        process_srt_file(input_file_path, output_file_path)

    print("All files processed successfully.")

if __name__ == "__main__":
        main()