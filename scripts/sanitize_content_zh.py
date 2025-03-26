import os
import csv
import argparse
import sys
import unicodedata
import string
from opencc import OpenCC

def parse_arguments():
    """
    Parses command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Sanitize the 'Content_zh' column in pretranslated CSV files by inserting appropriate spaces and converting Simplified Chinese to Traditional Chinese."
    )
    parser.add_argument(
        '-p', '--path',
        type=str,
        required=True,
        help="Path to the main directory containing 'pretranslated csv' folder."
    )
    parser.add_argument(
        '-i', '--input',
        type=str,
        default="pretranslated csv",
        help="Name of the input subdirectory containing CSV files (default: 'pretranslated csv')."
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default="sanitized csv",
        help="Name of the output subdirectory to save sanitized CSV files (default: 'sanitized csv')."
    )
    return parser.parse_args()

def is_ascii(char):
    """
    Determines if a character is an ASCII character.
    
    Parameters:
        char (str): A single character string.
    
    Returns:
        bool: True if the character is ASCII, False otherwise.
    """
    return ord(char) < 128
    
def is_full_width(char):
    """
    Determines if a character is full-width.
    
    Parameters:
        char (str): A single character string.
    
    Returns:
        bool: True if the character is full-width, False otherwise.
    """
    if len(char) != 1:
        return False
    east_asian_width = unicodedata.east_asian_width(char)
    return east_asian_width in ('F', 'W', 'A')  # Full-width, Wide, Ambiguous

def is_half_width(char):
    """
    Determines if a character is half-width.
    
    Parameters:
        char (str): A single character string.
    
    Returns:
        bool: True if the character is half-width, False otherwise.
    """
    if len(char) != 1:
        return False
    if is_ascii(char):
        return True
    east_asian_width = unicodedata.east_asian_width(char)
    return east_asian_width == 'H'  # Half-width

def is_full_width_punctuation(char):
    """
    Checks if a character is a full-width punctuation mark that should not have spaces inserted.
    
    Parameters:
        char (str): A single character string.
    
    Returns:
        bool: True if the character is a full-width punctuation mark, False otherwise.
    """
    full_width_punctuations = {
        '。', '，', '！', '？', '：', '；', '“', '”', '‘', '’', '（', '）', '「', '」', '『', '』', '《', '》',
        '、', '—', '…', '～', '·', '〈', '〉', '﹏', '｛', '｝', '［', '］', '【', '】',
        '﹐', '﹑', '﹒', '﹔', '﹖', '﹗', '﹕', '﹘', '﹝', '﹞', '﹟', '﹡',
        '﹢', '﹣', '﹤', '﹥', '﹦', '﹩', '﹪', '﹫', '﹬', '﹭', '﹮', '﹯',
    }
    return char in full_width_punctuations

def is_punctuation_space_or_nothing(char):
    """
    Determines if a character is a space or punctuation.
    
    Parameters:
        char (str): A single character string.
    
    Returns:
        bool: True if the character is a space or punctuation, False otherwise.
    """
    return char in string.whitespace or char in string.punctuation or char == ''

def sanitize_content(content, converter):
    """
    Converts Simplified Chinese to Traditional Chinese, then inserts spaces between adjacent half-width
    and full-width characters, excluding full-width punctuation marks.
    
    Parameters:
        content (str): The subtitle content in Chinese.
        converter (OpenCC): An instance of OpenCC for conversion.
    
    Returns:
        str: The sanitized content.
    """
    if not content:
        return content

    # Convert Simplified Chinese to Traditional Chinese
    traditional_content = converter.convert(content)

    sanitized = []
    prev_char = ''

    for char in traditional_content:
        if prev_char:
            if is_punctuation_space_or_nothing(prev_char) or is_punctuation_space_or_nothing(char):
                continue
            # Insert space if:
            # 1. Previous char is half-width and current is full-width and not punctuation
            # 2. Previous char is full-width (not punctuation) and current is half-width
            if (is_half_width(prev_char) and is_full_width(char) and not is_full_width_punctuation(char)):
                sanitized.append(' ')
            elif (is_full_width(prev_char) and not is_full_width_punctuation(prev_char) and is_half_width(char)):
                sanitized.append(' ')
        
        sanitized.append(char)
        prev_char = char

    return ''.join(sanitized)

def process_csv_file(input_path, output_path, converter):
    """
    Processes a single CSV file: reads 'Content_zh', sanitizes it, and writes to a new CSV file.
    
    Parameters:
        input_path (str): Path to the input CSV file.
        output_path (str): Path to save the sanitized CSV file.
        converter (OpenCC): An instance of OpenCC for conversion.
    """
    try:
        with open(input_path, 'r', encoding='utf-8-sig') as csv_infile:
            reader = csv.DictReader(csv_infile)
            fieldnames = reader.fieldnames
            if 'Content_zh' not in fieldnames:
                print(f"Warning: 'Content_zh' column not found in '{input_path}'. Skipping file.")
                return
            rows = list(reader)
        
        if not rows:
            print(f"Warning: No data found in '{input_path}'. Skipping file.")
            return
        
        # Sanitize 'Content_zh'
        for idx, row in enumerate(rows, start=1):
            original_content = row['Content_zh']
            sanitized_content = sanitize_content(original_content, converter)
            row['Content_zh'] = sanitized_content
            if idx <= 3:  # Print first few changes for verification
                print(f"Original: {original_content}")
                print(f"Sanitized: {sanitized_content}")
                print("---")
        
        # Write sanitized data to new CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as csv_outfile:
            writer = csv.DictWriter(csv_outfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"Successfully sanitized '{os.path.basename(input_path)}' and saved to '{os.path.basename(output_path)}'.\n")
    
    except Exception as e:
        print(f"Error processing '{input_path}': {e}")

def convert_all_csv_sanitize(input_directory, output_directory, converter):
    """
    Sanitizes all CSV files in the input directory and saves them to the output directory.
    
    Parameters:
        input_directory (str): Directory containing input CSV files.
        output_directory (str): Directory to save sanitized CSV files.
        converter (OpenCC): An instance of OpenCC for conversion.
    """
    # Ensure the output directory exists
    os.makedirs(output_directory, exist_ok=True)
    
    # List all CSV files in the input directory
    csv_files = [f for f in os.listdir(input_directory) if f.lower().endswith('.csv')]
    
    if not csv_files:
        print(f"No CSV files found in the '{input_directory}' folder.")
        return
    
    for csv_file in csv_files:
        input_file_path = os.path.join(input_directory, csv_file)
        base_name, ext = os.path.splitext(csv_file)
        output_file_name = f"{base_name}_sanitized{ext}"
        output_file_path = os.path.join(output_directory, output_file_name)
        
        print(f"Sanitizing '{csv_file}'...")
        process_csv_file(input_file_path, output_file_path, converter)

def main():
    args = parse_arguments()
    
    main_directory = args.path
    input_subdir = args.input
    output_subdir = args.output
    
    input_directory = os.path.join(main_directory, input_subdir)
    output_directory = os.path.join(main_directory, output_subdir)
    
    # Check if input directory exists
    if not os.path.isdir(input_directory):
        print(f"Error: Input subdirectory '{input_subdir}' not found in '{main_directory}'.")
        sys.exit(1)
    
    # Initialize OpenCC for Simplified to Traditional conversion
    converter = OpenCC('s2twp.json')  # 's2t' stands for Simplified to Traditional
    
    convert_all_csv_sanitize(input_directory, output_directory, converter)
    print("All files have been successfully sanitized and saved.")

if __name__ == "__main__":
    main()