import pandas as pd
import os

try:
    # Read the CSV file, only loading the text column
    print("Reading CSV file...")
    df = pd.read_csv('NOTEEVENTS.csv', usecols=['TEXT'])
    
    # Convert the text column to a list of strings
    text_list = df['TEXT'].tolist()
    
    # Save to a text file
    output_file = 'extracted_notes.txt'
    print(f"Saving {len(text_list)} notes to {output_file}...")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for text in text_list:
            # Write each note on a new line, replacing newlines within notes with spaces
            f.write(text.replace('\n', ' ') + '\n')
    
    print(f"Successfully saved notes to {output_file}")
    print(f"File size: {os.path.getsize(output_file) / (1024*1024):.2f} MB")
    
except Exception as e:
    print(f"An error occurred: {str(e)}") 