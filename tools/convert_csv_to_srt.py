import os
import csv
import argparse
import sys

def parse_arguments():
    """
    Parses command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Convert translated CSV files to SRT subtitle files."
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
        default="translated subtitles",
        help="Name of the output subdirectory to save translated SRT files (default: 'translated subtitles')."
    )
    return parser.parse_args()

def sanitize_content(content: str) -> str:
    """
    Sanitizes the content to ensure it doesn't contain any characters that could break the SRT format.

    Parameters:
        content (str): The subtitle content in Traditional Chinese.

    Returns:
        str: The sanitized content.
    """
    # Replace any occurrence of '-->' in the content which can break SRT formatting
    return content.replace('-->', '→')

def process_csv_file(input_path: str, output_path: str):
    """
    Processes a single CSV file: reads Timecode and Content_zh columns and writes to an SRT file.

    Parameters:
        input_path (str): Path to the input CSV file.
        output_path (str): Path to save the translated SRT file.
    """
    try:
        with open(input_path, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Check for required columns
            if 'Timecode' not in reader.fieldnames or 'Content_zh' not in reader.fieldnames:
                print(f"Warning: 'Timecode' or 'Content_zh' column not found in '{input_path}'. Skipping file.")
                return
            
            rows = list(reader)
        
        if not rows:
            print(f"Warning: No data found in '{input_path}'. Skipping file.")
            return
        
        with open(output_path, 'w', encoding='utf-8') as srtfile:
            for idx, row in enumerate(rows, start=1):
                timecode = row['Timecode'].strip()
                content = row['Content_zh'].strip()
                
                # Skip empty subtitles
                if not timecode or not content:
                    print(f"Warning: Empty Timecode or Content_zh at row {idx} in '{input_path}'. Skipping this subtitle.")
                    continue
                
                # Sanitize content
                content = sanitize_content(content)
                
                # Write to SRT format
                srtfile.write(f"{idx}\n")
                srtfile.write(f"{timecode}\n")
                srtfile.write(f"{content}\n\n")
        
        print(f"Successfully created SRT file: '{os.path.basename(output_path)}'")
    
    except Exception as e:
        print(f"Error processing '{input_path}': {e}")

def convert_all_csv_to_srt(input_directory: str, output_directory: str):
    """
    Converts all CSV files in the input directory to SRT files in the output directory.

    Parameters:
        input_directory (str): Directory containing input CSV files.
        output_directory (str): Directory to save output SRT files.
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
        base_name, _ = os.path.splitext(csv_file)
        output_file_name = f"{base_name}.srt"
        output_file_path = os.path.join(output_directory, output_file_name)
        
        print(f"Converting '{csv_file}' to '{output_file_name}'...")
        process_csv_file(input_file_path, output_file_path)

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
    
    convert_all_csv_to_srt(input_directory, output_directory)
    print("\nAll files have been successfully converted and saved.")

if __name__ == "__main__":
    main()