import os
import hashlib
from mutagen import File

def get_audio_metadata(file_path):
    """Extracts artist, title, and bitrate from an audio file."""
    try:
        audio = File(file_path)
        if audio is None:
            return None
        
        # Get bitrate (standardized to bps)
        bitrate = getattr(audio.info, 'bitrate', 0)
        
        # Extract tags (Artist and Title)
        # Mutagen keys vary by format, so we use a generic approach
        artist = str(audio.get('TPE1', audio.get('artist', ['Unknown Artist'])[0]))
        title = str(audio.get('TIT2', audio.get('title', ['Unknown Title'])[0]))
        
        return {
            'key': f"{artist.lower()}|{title.lower()}",
            'bitrate': bitrate,
            'path': file_path
        }
    except Exception:
        return None

def find_duplicates(root_dir):
    songs_registry = {}  # Key: artist|title, Value: list of file info
    duplicates = []

    print(f"--- Scanning directory: {root_dir} ---")

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.lower().endswith(('.mp3', '.flac', '.m4a', '.wav')):
                full_path = os.path.join(dirpath, filename)
                meta = get_audio_metadata(full_path)
                
                if meta and meta['key'] != "unknown artist|unknown title":
                    key = meta['key']
                    if key in songs_registry:
                        songs_registry[key].append(meta)
                    else:
                        songs_registry[key] = [meta]

    # Process registry for duplicates
    for key, files in songs_registry.items():
        if len(files) > 1:
            # Sort by bitrate descending (highest quality first)
            files.sort(key=lambda x: x['bitrate'], reverse=True)
            duplicates.append(files)

    return duplicates

import csv
from datetime import datetime


def compute_duplicate_stats(duplicates):
    total_duplicate_files = 0
    total_duplicate_size = 0
    artist_counts = {}

    for group in duplicates:
        total_duplicate_files += len(group)
        # Count all files so size includes all duplicates
        for track in group:
            try:
                total_duplicate_size += os.path.getsize(track['path'])
            except OSError:
                pass

        artist = group[0]['key'].split('|')[0].strip().title()
        artist_counts[artist] = artist_counts.get(artist, 0) + 1

    total_artists_with_duplicates = len(artist_counts)
    most_common_artist = None
    if artist_counts:
        most_common_artist = max(artist_counts.items(), key=lambda x: x[1])[0]

    return {
        'total_duplicate_files': total_duplicate_files,
        'total_duplicate_size': total_duplicate_size,
        'total_duplicates': len(duplicates),
        'artists_with_duplicates': total_artists_with_duplicates,
        'most_common_artist': most_common_artist,
        'artist_counts': artist_counts
    }


def write_csv_log(duplicates, output_path):
    header = ['group', 'quality', 'bitrate_kbps', 'path']
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)

        if not duplicates:
            writer.writerow(['No duplicates found', '', '', ''])
            return

        for group in duplicates:
            group_text = group[0]['key'].replace('|', ' - ').title()
            for i, track in enumerate(group):
                quality = 'HIGHER QUALITY' if i == 0 else 'LOWER QUALITY'
                bitrate = track['bitrate'] // 1000 if track['bitrate'] else 'Unknown'
                writer.writerow([group_text, quality, bitrate, track['path']])


def report_duplicates(duplicates, log_csv=None):
    if not duplicates:
        print("No duplicates found.")

    else:
        for group in duplicates:
            print(f"\nDuplicate found for: {group[0]['key'].replace('|', ' - ').title()}")
            for i, f in enumerate(group):
                quality_marker = "[HIGHER QUALITY]" if i == 0 else "[LOWER QUALITY]"
                bitrate_kbps = f['bitrate'] // 1000 if f['bitrate'] else "Unknown"
                print(f"  {quality_marker} {bitrate_kbps}kbps: {f['path']}")

    if log_csv:
        write_csv_log(duplicates, log_csv)
        print(f"\nCSV log written to {log_csv}")

    stats = compute_duplicate_stats(duplicates)
    print('\n=== Duplicate Stats ===')
    print(f"Total duplicate groups: {stats['total_duplicates']}")
    print(f"Total duplicate files: {stats['total_duplicate_files']}")
    size_mb = stats['total_duplicate_size'] / (1024*1024)
    print(f"Total duplicate space: {size_mb:.2f} MB")
    print(f"Artists with duplicates: {stats['artists_with_duplicates']}")
    print(f"Most common duplicate artist: {stats['most_common_artist'] if stats['most_common_artist'] else 'N/A'}")


if __name__ == "__main__":
    # Change this to your music directory path as needed
    target_folder = '/Volumes/Media/music/Tipper'
    log_file = f"duplicates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    dup_list = find_duplicates(target_folder)
    report_duplicates(dup_list, log_csv=log_file)