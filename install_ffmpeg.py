#!/usr/bin/env python3
"""
FFmpeg installer for Windows
Downloads and sets up FFmpeg for audio processing
"""

import os
import sys
import zipfile
import urllib.request
import tempfile
import shutil
from pathlib import Path

def download_ffmpeg():
    """Download and install FFmpeg for Windows"""
    print("🔧 Setting up FFmpeg for audio processing...")
    
    # FFmpeg download URL (static build)
    ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    
    # Create ffmpeg directory in project
    ffmpeg_dir = Path("ffmpeg")
    ffmpeg_dir.mkdir(exist_ok=True)
    
    # Check if already installed
    ffmpeg_exe = ffmpeg_dir / "bin" / "ffmpeg.exe"
    if ffmpeg_exe.exists():
        print(f"✅ FFmpeg already installed at: {ffmpeg_exe}")
        return str(ffmpeg_dir / "bin")
    
    try:
        print("📥 Downloading FFmpeg...")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_file:
            urllib.request.urlretrieve(ffmpeg_url, tmp_file.name)
            zip_path = tmp_file.name
        
        print("📦 Extracting FFmpeg...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Extract to temporary directory first
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_ref.extractall(temp_dir)
                
                # Find the extracted folder
                extracted_items = list(Path(temp_dir).iterdir())
                if not extracted_items:
                    raise Exception("No files extracted from zip")
                
                # Should be a single directory
                extracted_folder = extracted_items[0]
                if not extracted_folder.is_dir():
                    raise Exception("Expected a directory in the zip file")
                
                # Copy contents to our ffmpeg directory
                for item in extracted_folder.iterdir():
                    dest = ffmpeg_dir / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, dest)
        
        # Clean up
        os.unlink(zip_path)
        
        # Verify installation
        if ffmpeg_exe.exists():
            print(f"✅ FFmpeg installed successfully at: {ffmpeg_exe}")
            return str(ffmpeg_dir / "bin")
        else:
            raise Exception("FFmpeg executable not found after installation")
            
    except Exception as e:
        print(f"❌ Failed to install FFmpeg: {e}")
        print("💡 Manual installation:")
        print("   1. Download FFmpeg from https://ffmpeg.org/download.html")
        print("   2. Extract to C:\\ffmpeg\\")
        print("   3. Add C:\\ffmpeg\\bin to your PATH environment variable")
        return None

def add_to_path(ffmpeg_bin_path):
    """Add FFmpeg to PATH environment variable"""
    if ffmpeg_bin_path:
        current_path = os.environ.get("PATH", "")
        if ffmpeg_bin_path not in current_path:
            os.environ["PATH"] = current_path + os.pathsep + ffmpeg_bin_path
            print(f"✅ Added FFmpeg to PATH: {ffmpeg_bin_path}")
        else:
            print(f"✅ FFmpeg already in PATH")

if __name__ == "__main__":
    if os.name != 'nt':
        print("❌ This installer is for Windows only")
        print("💡 For other systems:")
        print("   - Ubuntu/Debian: sudo apt install ffmpeg")
        print("   - macOS: brew install ffmpeg")
        sys.exit(1)
    
    ffmpeg_bin = download_ffmpeg()
    if ffmpeg_bin:
        add_to_path(ffmpeg_bin)
        print("🎉 FFmpeg setup complete!")
        print("🔄 You may need to restart your application for changes to take effect.")
    else:
        sys.exit(1)
