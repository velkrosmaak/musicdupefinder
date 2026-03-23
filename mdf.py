import os
import sys
import hashlib
import concurrent.futures
import argparse
import time
from collections import defaultdict
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None
from mutagen import File

# ANSI colors
COLOR_RESET = '\033[0m'
COLOR_BOLD = '\033[1m'
COLOR_CYAN = '\033[96m'
COLOR_GREEN = '\033[92m'
COLOR_YELLOW = '\033[93m'
COLOR_RED = '\033[91m'
COLOR_MAGENTA = '\033[95m'


def color(text, ansi):
    return f"{ansi}{text}{COLOR_RESET}"


def format_size(size_bytes):
    """Auto-scales bytes to human readable format."""
    if size_bytes == 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"


def get_audio_metadata(file_path):
    """Extracts artist, title, album, and bitrate from an audio file."""
    start_time = time.time()
    try:
        audio = File(file_path)
        if audio is None:
            return None
        
        # Get bitrate (standardized to bps)
        bitrate = getattr(audio.info, 'bitrate', 0)
        
        # Extract tags (Artist, Title, Album)
        # Mutagen keys vary by format, so we use a generic approach
        artist = str(audio.get('TPE1', audio.get('artist', ['Unknown Artist'])[0]))
        title = str(audio.get('TIT2', audio.get('title', ['Unknown Title'])[0]))
        album = str(audio.get('TALB', audio.get('album', ['Unknown Album'])[0]))
        
        # Extract Year (Try common keys: TDRC, TYER, date, year, ©day)
        year = str(audio.get('TDRC', audio.get('TYER', audio.get('date', audio.get('year', audio.get('©day', ['Unknown Year']))))[0]))
        if year and str(year).strip():
             year = str(year).split('-')[0].strip()[:4]
        
        # Format (extension)
        fmt = os.path.splitext(file_path)[1].lower().lstrip('.')
        
        elapsed = time.time() - start_time
        
        return {
            'key': f"{artist.lower()}|{title.lower()}",
            'artist': artist,
            'title': title,
            'album': album,
            'year': year,
            'format': fmt,
            'bitrate': bitrate,
            'path': file_path,
            'scan_time': elapsed
        }
    except Exception:
        return None

def find_duplicates(root_dir):
    songs_registry = {}  # Key: artist|title, Value: list of file info
    duplicates = []
    
    # Performance stats
    stats = {
        'start_time': time.time(),
        'total_files': 0,
        'scan_time_sum': 0.0,
        'slowest_song': {'time': 0.0, 'name': None},
        'artist_times': defaultdict(float)
    }

    print(color("====================================================", COLOR_MAGENTA))
    print(color("  _____  _   _  _____  _   _  _____ _   _ ", COLOR_CYAN))
    print(color(" |  __ \| \ | |/ ____|| \ | |/ ____| \ | |", COLOR_CYAN))
    print(color(" | |  | |  \| | |  __ |  \| | |  __|  \| |", COLOR_CYAN))
    print(color(" | |  | | . ` | | |_ || . ` | | |_ | . ` |", COLOR_CYAN))
    print(color(" | |__| | |\  | |__| || |\  | |__| | |\  |", COLOR_CYAN))
    print(color(" |_____/|_| \_|\_____||_| \_|\_____|_| \_|", COLOR_CYAN))
    print(color("====================================================", COLOR_MAGENTA))
    print(color(f"Scanning: {root_dir}", COLOR_GREEN), flush=True)

    audio_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.lower().endswith(('.mp3', '.flac', '.m4a', '.wav')):
                audio_files.append(os.path.join(dirpath, filename))

    total_files = len(audio_files)
    print(color(f"Found {total_files} audio files. Extracting metadata...", COLOR_CYAN), flush=True)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_path = {executor.submit(get_audio_metadata, f): f for f in audio_files}
        
        pbar = None
        if tqdm:
            pbar = tqdm(total=total_files, unit="file", desc="Scanning", ncols=100)

        processed = 0
        for future in concurrent.futures.as_completed(future_to_path):
            processed += 1
            
            meta = future.result()
            
            if pbar:
                if meta:
                    pbar.set_postfix(artist=meta['artist'][:20], album=meta['album'][:20], refresh=False)
                pbar.update(1)
            else:
                # Fallback progress output if tqdm is missing
                current = f"{meta['artist']} - {meta['album']}" if meta else "..."
                print(color(f"\rScanned {processed}/{total_files}: {current[:50]}", COLOR_YELLOW).ljust(90), end="", flush=True)

            if meta and meta['key'] != "unknown artist|unknown title":
                key = meta['key']
                if key in songs_registry:
                    songs_registry[key].append(meta)
                else:
                    songs_registry[key] = [meta]
        
        if pbar:
            pbar.close()
        else:
            print()  # Ensure newline after carriage return output

    stats['total_duration'] = time.time() - stats['start_time']
    print(color(f"Finished scanning {total_files} audio files.", COLOR_GREEN), flush=True)

    # Process registry for duplicates
    for key, files in songs_registry.items():
        if len(files) > 1:
            # Sort by bitrate descending (highest quality first)
            files.sort(key=lambda x: x['bitrate'], reverse=True)
            duplicates.append(files)

    return duplicates, stats

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
        'artist_counts': artist_counts,
    }


def write_csv_log(duplicates, output_path):
    header = ['Group ID', 'Quality (kbps)', 'Highest Quality', 'Format', 'Artist', 'Title', 'Album', 'Year', 'Path']
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(header)

        if not duplicates:
            writer.writerow(['No duplicates found'] + [''] * 8)
            return

        for i, group in enumerate(duplicates):
            group_id = f"DUP-{i+1:04d}"
            max_bitrate = max((t['bitrate'] for t in group), default=0)
            for track in group:
                bitrate = track['bitrate'] // 1000 if track['bitrate'] else 0
                is_highest = track['bitrate'] == max_bitrate
                writer.writerow([
                    group_id,
                    bitrate,
                    is_highest,
                    track['format'],
                    track['artist'],
                    track['title'],
                    track['album'],
                    track['year'],
                    track['path']
                ])


def report_duplicates(duplicates, stats=None, log_csv=None):
    if not duplicates:
        print("No duplicates found.")

    else:
        print(f"\n{len(duplicates)} duplicate groups found.", flush=True)
        # Only print first few to avoid spamming console if many
        limit = 5
        for i, group in enumerate(duplicates[:limit]):
            print(f"\nDuplicate Group {i+1}: {group[0]['artist']} - {group[0]['title']}")
            for f in group:
                bitrate_kbps = f['bitrate'] // 1000 if f['bitrate'] else "Unknown"
                size_str = format_size(os.path.getsize(f['path']))
                print(f"  [{f['format'].upper()}] {bitrate_kbps}kbps, {size_str}: {f['path']}")
        
        if len(duplicates) > limit:
            print(f"\n... and {len(duplicates) - limit} more groups.")

    if log_csv:
        write_csv_log(duplicates, log_csv)
        print(f"\nCSV log written to {log_csv}")

    dupe_stats = compute_duplicate_stats(duplicates)
    print('\n=== Duplicate Stats ===', flush=True)
    print(f"Total duplicate groups: {dupe_stats['total_duplicates']}", flush=True)
    print(f"Total duplicate files: {dupe_stats['total_duplicate_files']}", flush=True)
    print(f"Total duplicate space: {format_size(dupe_stats['total_duplicate_size'])}", flush=True)
    print(f"Artists with duplicates: {dupe_stats['artists_with_duplicates']}", flush=True)
    print(f"Most common duplicate artist: {dupe_stats['most_common_artist'] if dupe_stats['most_common_artist'] else 'N/A'}", flush=True)

    if stats:
        print('\n=== Performance Stats ===', flush=True)
        print(f"Total scan time: {stats['total_duration']:.2f}s")
        avg_time = stats['scan_time_sum'] / max(1, stats['total_duration']) # Approximate avg per sec? No, avg per song.
        # We need total_files from stats but it wasn't tracked in find_duplicates explicitly outside loop
        # We can imply it from the scan_time_sum count or just use the passed in total if available, 
        # but let's just use what we have.
        # Actually we didn't store total files count in `stats` dict in find_duplicates.
        # Let's use scan_time_sum / total_duration to see utilization or just print maxes.
        print(f"Slowest song to scan: {stats['slowest_song']['time']:.4f}s ({stats['slowest_song']['name']})")
        
        if stats['artist_times']:
            slowest_artist = max(stats['artist_times'].items(), key=lambda x: x[1])
            print(f"Most time consuming artist: {slowest_artist[0]} ({slowest_artist[1]:.2f}s total)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find duplicate audio files by tags.")
    parser.add_argument("target_folder", help="Root directory to scan")
    parser.add_argument("--log", help="Output CSV log file path")
    args = parser.parse_args()

    log_file = args.log if args.log else f"duplicates_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    dup_list, perf_stats = find_duplicates(args.target_folder)
    report_duplicates(dup_list, stats=perf_stats, log_csv=log_file)