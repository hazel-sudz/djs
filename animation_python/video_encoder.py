"""
Video encoding with hardware acceleration (VideoToolbox on M2).

Uses FFmpeg with VideoToolbox for hardware-accelerated H.265/HEVC encoding.
"""

import subprocess
import shutil
from pathlib import Path
import time


def check_ffmpeg() -> bool:
    """Check if FFmpeg is available."""
    return shutil.which("ffmpeg") is not None


def check_hardware_encoders() -> dict:
    """Check available hardware encoders."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-encoders"],
            capture_output=True,
            text=True
        )
        output = result.stdout + result.stderr

        return {
            "hevc_videotoolbox": "hevc_videotoolbox" in output,
            "h264_videotoolbox": "h264_videotoolbox" in output,
            "prores_videotoolbox": "prores_videotoolbox" in output,
        }
    except Exception:
        return {}


def create_video(
    frames_dir: str,
    output_file: str,
    frame_rate: float = 1.0,
    use_hevc: bool = True,
    quality: int = 65,
) -> str:
    """Create video from PNG frames using hardware-accelerated encoding.

    Args:
        frames_dir: Directory containing frame_XXXX.png files
        output_file: Output video file path
        frame_rate: Frames per second
        use_hevc: Use HEVC (H.265) instead of H.264
        quality: Quality level (0-100, higher is better)

    Returns:
        Path to created video file
    """
    if not check_ffmpeg():
        raise RuntimeError("FFmpeg not found. Install with: brew install ffmpeg")

    frames_path = Path(frames_dir)
    frame_files = sorted(frames_path.glob("frame_*.png"))

    if not frame_files:
        raise ValueError(f"No frame files found in {frames_dir}")

    print("\n=== Hardware-Accelerated Video Encoding ===")
    print(f"  Frames: {len(frame_files)}")
    print(f"  Frame rate: {frame_rate} fps")

    # Check available encoders
    encoders = check_hardware_encoders()

    if use_hevc and encoders.get("hevc_videotoolbox"):
        encoder = "hevc_videotoolbox"
        extra_opts = ["-tag:v", "hvc1"]  # Better compatibility
    elif encoders.get("h264_videotoolbox"):
        encoder = "h264_videotoolbox"
        extra_opts = []
    else:
        print("  Warning: Hardware encoding not available, using software")
        encoder = "libx264"
        extra_opts = ["-crf", "18"]

    print(f"  Encoder: {encoder}")

    # Build FFmpeg command
    input_pattern = str(frames_path / "frame_%04d.png")

    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(frame_rate),
        "-i", input_pattern,
        "-c:v", encoder,
    ]

    if encoder.endswith("_videotoolbox"):
        cmd.extend(["-q:v", str(quality)])

    cmd.extend(extra_opts)
    cmd.extend(["-pix_fmt", "yuv420p", output_file])

    # Run encoding
    start_time = time.time()

    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        # Fallback to software encoding
        print("  Hardware encoding failed, trying software...")
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(frame_rate),
            "-i", input_pattern,
            "-c:v", "libx264",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            output_file
        ]
        subprocess.run(cmd, check=True, capture_output=True)

    elapsed = time.time() - start_time
    file_size = Path(output_file).stat().st_size / 1024 / 1024

    print(f"  Video created: {output_file}")
    print(f"  File size: {file_size:.2f} MB")
    print(f"  Encoding time: {elapsed:.1f} seconds")
    print("=== Video Encoding Complete ===\n")

    return output_file


def cleanup_frames(frames_dir: str, pattern: str = "frame_*.png"):
    """Remove frame files after video creation."""
    frames_path = Path(frames_dir)
    frame_files = list(frames_path.glob(pattern))

    if frame_files:
        print(f"Removing {len(frame_files)} frame files...")
        for f in frame_files:
            f.unlink()
        print("Cleanup complete")
