import os
import re
import argparse
import csv
import sys
from datetime import datetime

def parse_arguments():
    """
    Parses command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Extract subtitles from preprocessed SRT files into CSV format."
    )
    parser.add_argument(
        '-p', '--path',
        type=str,
        required=True,
        help="Path to the main directory containing 'preprocessed subtitles' folder."
    )
    parser.add_argument(
        '-i', '--input',
        type=str,
        default="preprocessed subtitles",
        help="Name of the input subdirectory containing preprocessed SRT files (default: 'preprocessed subtitles')."
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default="extracted csv",
        help="Name of the output subdirectory to save extracted CSV files (default: 'extracted csv')."
    )
    return parser.parse_args()

def parse_time(time_str):
    """
    Parses a time string from SRT format to a datetime object.
    Example: "00:01:15,123" -> datetime object
    """
    try:
        return datetime.strptime(time_str, "%H:%M:%S,%f")
    except ValueError as e:
        print(f"Error parsing time '{time_str}': {e}")
        return None

class Subtitle:
    def __init__(self, number, start, end, text):
        self.number = number  # int
        self.start = start    # datetime
        self.end = end        # datetime
        self.text = text      # list of strings
    
    def timecode(self):
        """
        Returns the timecode in SRT format.
        Example: "00:01:15,123 --> 00:01:18,456"
        """
        return f"{format_time(self.start)} --> {format_time(self.end)}"

def format_time(time_obj):
    """
    Formats a datetime object to SRT time string.
    Example: datetime object -> "00:01:15,123"
    """
    return time_obj.strftime("%H:%M:%S,%f")[:-3]

def read_srt(file_path):
    """
    Reads an SRT file and returns a list of Subtitle objects.
    """
    subtitles = []
    with open(file_path, 'r', encoding='utf-8-sig') as file:
        content = file.read()
    
    # Split content into blocks separated by blank lines
    blocks = re.split(r'\n\s*\n', content.strip(), flags=re.MULTILINE)
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            try:
                number = int(lines[0].strip())
            except ValueError:
                print(f"Warning: Invalid subtitle number '{lines[0]}' in file '{file_path}'. Skipping block.")
                continue
            
            time_match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', lines[1].strip())
            if time_match:
                start_time = parse_time(time_match.group(1))
                end_time = parse_time(time_match.group(2))
                if not start_time or not end_time:
                    print(f"Warning: Invalid timecodes in subtitle number {number} in file '{file_path}'. Skipping block.")
                    continue
                text = ' '.join(lines[2:]).strip()
                subtitles.append(Subtitle(number, start_time, end_time, text))
            else:
                print(f"Warning: Time format incorrect in subtitle number {number} in file '{file_path}'. Skipping block.")
    return subtitles

def write_csv(subtitles, csv_path):
    """
    Writes a list of Subtitle objects to a CSV file with two columns: Timecode and Content.
    """
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Timecode', 'Content'])  # Header
        for subtitle in subtitles:
            writer.writerow([subtitle.timecode(), subtitle.text])

def process_srt_file(srt_path, csv_path):
    """
    Processes a single SRT file: reads, parses, and writes to a CSV file.
    """
    subtitles = read_srt(srt_path)
    if not subtitles:
        print(f"No valid subtitles found in '{srt_path}'. Skipping file.")
        return
    write_csv(subtitles, csv_path)
    print(f"Converted '{os.path.basename(srt_path)}' -> '{os.path.basename(csv_path)}'")

def main():
    args = parse_arguments()
    
    main_directory = args.path
    input_subdir = args.input
    output_subdir = args.output
    
    # Validate main directory
    if not os.path.isdir(main_directory):
        print(f"Error: The specified path '{main_directory}' is not a valid directory.")
        sys.exit(1)
    
    input_directory = os.path.join(main_directory, input_subdir)
    if not os.path.isdir(input_directory):
        print(f"Error: Input subdirectory '{input_subdir}' not found in '{main_directory}'.")
        sys.exit(1)
    
    output_directory = os.path.join(main_directory, output_subdir)
    os.makedirs(output_directory, exist_ok=True)
    
    # Find all .srt files in the input directory
    srt_files = [f for f in os.listdir(input_directory) if f.lower().endswith('.srt')]
    
    if not srt_files:
        print(f"No .srt files found in the '{input_subdir}' folder.")
        sys.exit(1)
    
    for srt_file in srt_files:
        srt_path = os.path.join(input_directory, srt_file)
        base_name, _ = os.path.splitext(srt_file)
        csv_file_name = f"{base_name}.csv"
        csv_path = os.path.join(output_directory, csv_file_name)
        process_srt_file(srt_path, csv_path)
    
    print("All files have been successfully converted to CSV format.")

if __name__ == "__main__":
    main()