import os
import subprocess
import sys
from pathlib import Path
import noisereduce as nr
import shutil
import soundfile as sf

def open_explorer(path):
    """Open file explorer at the specified path."""
    resolved_path = Path(path).resolve()
    subprocess.run(["xdg-open", str(resolved_path)])

# Get video name and processing mode from user
video_name = input("¿cuál es el nombre del video final? ")
is_manual = input("¿Quieres limpiar el audio manualmente? (s/n): ").strip().lower() == 's'

# Create directory structure
# Main evidence directory
evidence_dir = Path(f"./evidence/{video_name}")
evidence_dir.mkdir(parents=True, exist_ok=True)

# Resources subdirectory
resources_dir = evidence_dir / "res"
resources_dir.mkdir(parents=True, exist_ok=True)

# Audio subdirectory
audio_dir = evidence_dir / "audio"
audio_dir.mkdir(parents=True, exist_ok=True)

# Define source paths
downloads_dir = Path.home() / "Downloads"
source_video = downloads_dir / "video.webm"

# Define intermediate files
temp_cleaned_audio = evidence_dir / "audio/cleaned_audio.wav"

# Define output files
final_video = resources_dir / f"{video_name}_output.mp4"
compressed_video = evidence_dir / f"{video_name}_compressed.mp4"

# Define archive files (original files saved in the evidence directory)
archived_video_webm = resources_dir / f"{video_name}_input.webm"
archived_video_mp4 = resources_dir / f"{video_name}_input.mp4"
archived_raw_audio = audio_dir / f"{video_name}_input.wav"
archived_clean_audio = audio_dir / f"{video_name}_clean.wav"

# Define source_audio in the evidence directory
source_audio = archived_raw_audio

# Move original video to the destination directory *before* processing
try:
    shutil.move(str(source_video.resolve()), str(archived_video_webm.resolve()))
    print(f"Archivo original movido a {archived_video_webm.resolve()}")
    source_video = archived_video_webm  # Update variable to use the new path
    converted_video = resources_dir / f"{video_name}_input.mp4"  # Define converted_video in the resources directory
except FileNotFoundError:
    print(f"Error: no se encontró el archivo original {source_video.resolve()}")
    sys.exit(1)

# 1. Convert to mp4
subprocess.run(
    ["ffmpeg", "-i", str(source_video.resolve()), "-c:v", "libx264", str(converted_video.resolve())],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)

# 2. Extract audio directly to the evidence directory
subprocess.run(
    ["ffmpeg", "-i", str(converted_video.resolve()), "-q:a", "0", "-map", "a", str(source_audio.resolve())],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)

if is_manual:
    # 3. Manual audio cleaning
    print("➡️ Sube el archivo a Adobe Enhance manualmente:")
    print(f"Archivo: {source_audio.resolve()}")

    # Open file explorer in the audio directory
    open_explorer(audio_dir)

    input("Presiona ENTER cuando tengas el audio limpio y renombrado a 'cleaned_audio.wav'...")

    if not temp_cleaned_audio.exists():
        print("Error: no se encontró el archivo 'cleaned_audio.wav'. El script se detendrá.")
        sys.exit(1)

else:
    # 3. Automatic audio cleaning with noisereduce
    print("Limpiando audio automáticamente con noisereduce...")
    audio_data, rate = sf.read(source_audio)
    reduced_noise = nr.reduce_noise(y=audio_data, sr=rate)
    sf.write(temp_cleaned_audio, reduced_noise, rate)
    print(f"Audio limpio generado: {temp_cleaned_audio.resolve()}")

# 4. Merge video and cleaned audio (with error capture)
result = subprocess.run(
    [
        "ffmpeg",
        "-i",
        str(converted_video.resolve()),
        "-i",
        str(temp_cleaned_audio.resolve()),
        "-c:v",
        "copy",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-shortest",
        str(final_video.resolve()),
    ],
    capture_output=True,
    text=True,
)

if result.returncode != 0:
    print("Error al unir video y audio:")
    print(result.stderr)
    sys.exit(1)

# 5. Compress the result
subprocess.run(
    [
        "ffmpeg",
        "-i",
        str(final_video.resolve()),
        "-vcodec",
        "libx264",
        "-crf",
        "23",
        str(compressed_video.resolve()),
    ],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)

# Move cleaned audio file to the final location
temp_cleaned_audio.rename(archived_clean_audio)

# Move converted mp4 to archive
converted_video.rename(archived_video_mp4)

print("Proceso completado con éxito.")

# Open the evidence directory in file explorer
open_explorer(evidence_dir)
