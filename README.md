# Music Dupe Finder

A high-performance, multi-threaded Python script to scan directories for duplicate audio files. It identifies duplicates based on metadata tags (Artist, Album, Title) rather than just filenames, allowing you to find copies regardless of how they are named.

## Features

- **Multi-threaded**: rapid scanning and metadata extraction.
- **Format Support**: MP3, FLAC, M4A, WAV.
- **Tag-based Matching**: Identifies duplicates even if filenames differ.
- **Detailed Reporting**: Generates a CSV log and provides real-time progress.

## Setup

It is recommended to use a virtual environment (`venv`) to keep dependencies isolated.

1. **Create a virtual environment:**
   ```bash
   python3 -m venv venv
   ```

2. **Activate the virtual environment:**
   - **macOS / Linux:**
     ```bash
     source venv/bin/activate
     ```
   - **Windows:**
     ```bash
     .\venv\Scripts\activate
     ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the script by providing the target folder you want to scan:

```bash
python mdf.py "/path/to/your/music"
```

### Optional Arguments

- `--log <filename>`: Specify a custom output path for the CSV log.
  ```bash
  python mdf.py "/Users/me/Music" --log duplicates.csv
  ```