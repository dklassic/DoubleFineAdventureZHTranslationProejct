import os
import csv
import argparse
import openai
import sys
import time
import re
from typing import List

def parse_arguments():
    """
    Parses command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Translate the 'Content' column of CSV files to Traditional Chinese using OpenAI GPT-4 API."
    )
    parser.add_argument(
        '-p', '--path',
        type=str,
        required=True,
        help="Path to the main directory containing 'extracted csv' folder."
    )
    parser.add_argument(
        '-i', '--input',
        type=str,
        default="extracted csv",
        help="Name of the input subdirectory containing CSV files (default: 'extracted csv')."
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default="pretranslated csv",
        help="Name of the output subdirectory to save translated CSV files (default: 'pretranslated csv')."
    )
    parser.add_argument(
        '-k', '--api_key',
        type=str,
        default=None,
        help="Your OpenAI API key. If not provided, the script will look for the 'OPENAI_API_KEY' environment variable."
    )
    return parser.parse_args()

def initialize_openai(api_key: str):
    """
    Initializes the OpenAI API with the provided API key.
    """
    openai.api_key = api_key

def construct_translation_prompt(subtitles: List[str]) -> str:
    """
    Constructs a prompt to translate multiple subtitles to Traditional Chinese with specific context and terminology guidelines.
    
    Parameters:
        subtitles (List[str]): List of subtitle texts in English.
    
    Returns:
        str: The constructed prompt.
    """
    prompt = (
        "You are a proficient translator working on a documentary about game development by Double Fine studio. "
        "Translate the following English subtitles to Traditional Chinese suitable for a Taiwanese audience. "
        "Ensure that all translated terminologies comply with Taiwan's usage and avoid using any China-specific terminologies. "
        "Maintain the numbering and formatting as shown.\n\n"
    )
    for idx, subtitle in enumerate(subtitles, start=1):
        # Escape any quotes in subtitles to prevent prompt formatting issues
        clean_subtitle = subtitle.replace('"', '\\"')
        prompt += f"{idx}. \"{clean_subtitle}\"\n"
    prompt += "\nProvide the translations in the same numbered format.\n\nTranslated Subtitles:\n"
    return prompt

def parse_translation_response(response: str, expected_count: int) -> List[str]:
    """
    Parses the API response to extract translated subtitles.
    
    Parameters:
        response (str): The raw response from the API.
        expected_count (int): The number of subtitles expected.
    
    Returns:
        List[str]: List of translated subtitles.
    """
    # Extract numbered translations using regex
    pattern = re.compile(r'^\d+\.\s*"(.*?)"', re.MULTILINE)
    matches = pattern.findall(response)
    
    if len(matches) != expected_count:
        print(f"Warning: Expected {expected_count} translations but got {len(matches)}.")
    
    return matches

def translate_batch(subtitles: List[str], max_retries: int = 5, backoff_factor: int = 2) -> List[str]:
    """
    Translates a batch of subtitles to Traditional Chinese using OpenAI's GPT-4 API.
    
    Parameters:
        subtitles (List[str]): List of subtitle texts in English.
        max_retries (int): Maximum number of retries for failed API calls.
        backoff_factor (int): Factor by which the delay increases after each failed attempt.
    
    Returns:
        List[str]: List of translated subtitles in Traditional Chinese.
    """
    if not subtitles:
        return []
    
    prompt = construct_translation_prompt(subtitles)
    
    for attempt in range(1, max_retries + 1):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a highly skilled translator specializing in translating English content to Traditional Chinese "
                            "for Taiwanese audiences, especially in the context of game development documentaries."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0  # deterministic output
            )
            translation = response.choices[0].message['content'].strip()
            translated_subtitles = parse_translation_response(translation, len(subtitles))
            return translated_subtitles
        except openai.error.RateLimitError:
            wait_time = backoff_factor ** attempt
            print(f"[Attempt {attempt}/{max_retries}] Rate limit exceeded. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
        except openai.error.OpenAIError as e:
            wait_time = backoff_factor ** attempt
            print(f"[Attempt {attempt}/{max_retries}] OpenAI API error: {e}. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
    
    print(f"Failed to translate batch after {max_retries} attempts. Returning empty translations.")
    return [""] * len(subtitles)

def split_into_chunks(lst: List[str], chunk_size: int = 50) -> List[List[str]]:
    """
    Splits a list into smaller chunks.
    
    Parameters:
        lst (List[str]): The list to split.
        chunk_size (int): The maximum size of each chunk.
    
    Returns:
        List[List[str]]: A list of chunks.
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def process_csv_file(input_path: str, output_path: str, chunk_size: int = 50):
    """
    Processes a single CSV file: reads all subtitles, translates them in batch, and writes to a new CSV file.
    
    Parameters:
        input_path (str): Path to the input CSV file.
        output_path (str): Path to save the translated CSV file.
        chunk_size (int): Number of subtitles to translate in each batch.
    """
    try:
        with open(input_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            if 'Content' not in reader.fieldnames:
                print(f"Warning: 'Content' column not found in '{input_path}'. Skipping file.")
                return
            rows = list(reader)
        
        subtitles = [row['Content'] for row in rows]
        print(f"Translating '{os.path.basename(input_path)}' with {len(subtitles)} subtitles...")
        
        translated_subtitles = []
        chunks = split_into_chunks(subtitles, chunk_size)
        for idx, chunk in enumerate(chunks, start=1):
            print(f"Translating chunk {idx}/{len(chunks)}...")
            translations = translate_batch(chunk)
            if len(translations) != len(chunk):
                print(f"Warning: Mismatch in translations for chunk {idx}. Some translations may be missing.")
            translated_subtitles.extend(translations)
        
        if not translated_subtitles:
            print(f"Warning: No translations obtained for '{input_path}'. Skipping file.")
            return
        
        # Add the translated subtitles to rows
        for row, translation in zip(rows, translated_subtitles):
            row['Content_zh'] = translation
        
        # Define fieldnames for the output CSV
        fieldnames = reader.fieldnames + ['Content_zh']
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"Saved translated CSV to '{os.path.basename(output_path)}'\n")
    
    except Exception as e:
        print(f"Error processing '{input_path}': {e}")

def process_all_csv_files(csv_files: List[str], input_directory: str, output_directory: str, chunk_size: int = 50):
    """
    Processes all CSV files by translating their contents.
    
    Parameters:
        csv_files (List[str]): List of CSV filenames to process.
        input_directory (str): Directory where input CSVs are located.
        output_directory (str): Directory to save translated CSVs.
        chunk_size (int): Number of subtitles to translate in each batch.
    """
    for csv_file in csv_files:
        input_file_path = os.path.join(input_directory, csv_file)
        base_name, ext = os.path.splitext(csv_file)
        output_file_name = f"{base_name}_pretranslated{ext}"
        output_file_path = os.path.join(output_directory, output_file_name)
        process_csv_file(input_file_path, output_file_path, chunk_size)

def main():
    args = parse_arguments()
    
    # Retrieve API key from environment variable if not provided
    if args.api_key:
        api_key = args.api_key
    else:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("Error: OpenAI API key not provided. Use the '--api_key' argument or set the 'OPENAI_API_KEY' environment variable.")
            sys.exit(1)
    
    # Initialize OpenAI API
    initialize_openai(api_key)
    
    main_directory = args.path
    input_subdir = args.input
    output_subdir = args.output
    
    input_directory = os.path.join(main_directory, input_subdir)
    if not os.path.isdir(input_directory):
        print(f"Error: Input subdirectory '{input_subdir}' not found in '{main_directory}'.")
        sys.exit(1)
    
    output_directory = os.path.join(main_directory, output_subdir)
    os.makedirs(output_directory, exist_ok=True)
    
    # Find all .csv files in the input directory
    csv_files = [f for f in os.listdir(input_directory) if f.lower().endswith('.csv')]
    
    if not csv_files:
        print(f"No .csv files found in the '{input_subdir}' folder.")
        sys.exit(1)
    
    # Process all CSV files
    process_all_csv_files(csv_files, input_directory, output_directory)
    
    print("All files have been successfully translated and saved.")

if __name__ == "__main__":
    main()