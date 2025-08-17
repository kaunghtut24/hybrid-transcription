"""
Audio file upload handler with validation and secure temporary storage
"""

import os
import tempfile
import uuid
import mimetypes
import shutil
from typing import Dict, Any, Optional, Tuple, Callable
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import threading
import time
import functools

# Optional import for MIME type detection
try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

from .base import BaseService, FileHandlerInterface, ValidationError, ProcessingError
from .models import FileUploadSession


class FileOperationError(ProcessingError):
    """Specific error for file operations with retry capability"""
    def __init__(self, message: str, error_code: str = None, retryable: bool = False, 
                 recovery_suggestions: Optional[list] = None):
        super().__init__(message, error_code)
        self.retryable = retryable
        self.recovery_suggestions = recovery_suggestions or []


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff_factor: float = 2.0,
                    retryable_exceptions: tuple = (OSError, IOError, PermissionError)):
    """Decorator for retrying file operations on transient failures"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = delay * (backoff_factor ** attempt)
                        time.sleep(wait_time)
                        continue
                    else:
                        # Final attempt failed
                        raise FileOperationError(
                            f"Operation failed after {max_retries + 1} attempts: {str(e)}",
                            error_code="RETRY_EXHAUSTED",
                            retryable=False,
                            recovery_suggestions=[
                                "Check disk space and permissions",
                                "Verify the file is not locked by another process",
                                "Try uploading a smaller file",
                                "Contact support if the issue persists"
                            ]
                        )
                except Exception as e:
                    # Non-retryable exception
                    raise e
            
            # Should never reach here, but just in case
            raise last_exception
        
        return wrapper
    return decorator


class AudioFileHandler(BaseService, FileHandlerInterface):
    """Handler for audio file uploads with validation and secure storage"""
    
    # Supported audio formats with their MIME types
    SUPPORTED_FORMATS = {
        'mp3': ['audio/mpeg', 'audio/mp3'],
        'wav': ['audio/wav', 'audio/wave', 'audio/x-wav'],
        'm4a': ['audio/mp4', 'audio/x-m4a'],
        'flac': ['audio/flac', 'audio/x-flac'],
        'mp4': ['audio/mp4', 'video/mp4'],
        'wma': ['audio/x-ms-wma'],
        'aac': ['audio/aac', 'audio/x-aac'],
        'ogg': ['audio/ogg', 'audio/x-ogg']
    }
    
    # Maximum file size (100MB)
    MAX_FILE_SIZE = 100 * 1024 * 1024
    
    # Maximum filename length
    MAX_FILENAME_LENGTH = 255
    
    # Temporary file cleanup interval (seconds)
    CLEANUP_INTERVAL = 3600  # 1 hour
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.temp_dir = self.get_config_value('temp_dir', tempfile.gettempdir())
        self.max_file_size = self.get_config_value('max_file_size', self.MAX_FILE_SIZE)
        self.cleanup_interval = self.get_config_value('cleanup_interval', self.CLEANUP_INTERVAL)
        
        # Dictionary to track temporary files for cleanup
        self._temp_files = {}
        self._cleanup_lock = threading.Lock()
        
        # Start cleanup thread
        self._start_cleanup_thread()
        
        self.logger.info(f"AudioFileHandler initialized with temp_dir: {self.temp_dir}")
    
    def validate_config(self) -> bool:
        """Validate service configuration"""
        try:
            # Check if temp directory exists and is writable
            if not os.path.exists(self.temp_dir):
                os.makedirs(self.temp_dir, exist_ok=True)
            
            # Test write permissions
            test_file = os.path.join(self.temp_dir, f"test_{uuid.uuid4().hex}")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            
            return True
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False
    
    def validate_file(self, file_data: FileStorage) -> Dict[str, Any]:
        """
        Validate uploaded audio file with comprehensive error handling
        
        Args:
            file_data: Werkzeug FileStorage object
            
        Returns:
            Dict containing validation results and file metadata
            
        Raises:
            ValidationError: If file validation fails
        """
        validation_result = {
            'is_valid': False,
            'errors': [],
            'warnings': [],
            'metadata': {},
            'recovery_suggestions': []
        }
        
        try:
            # Check if file is provided
            if not file_data or not file_data.filename:
                validation_result['errors'].append("No file provided")
                validation_result['recovery_suggestions'].append("Please select a file to upload")
                return validation_result
            
            # Validate filename
            original_filename = file_data.filename
            filename = secure_filename(original_filename)
            
            if not filename:
                validation_result['errors'].append("Invalid filename - contains only special characters")
                validation_result['recovery_suggestions'].extend([
                    "Rename your file to use only letters, numbers, and basic punctuation",
                    "Avoid special characters like: < > : \" | ? * \\"
                ])
                return validation_result
            
            if len(filename) > self.MAX_FILENAME_LENGTH:
                validation_result['errors'].append(f"Filename too long ({len(filename)} characters, max {self.MAX_FILENAME_LENGTH})")
                validation_result['recovery_suggestions'].extend([
                    f"Shorten the filename to under {self.MAX_FILENAME_LENGTH} characters",
                    "Consider using abbreviations or removing unnecessary words"
                ])
                return validation_result
            
            # Get file extension
            file_extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
            if not file_extension:
                validation_result['errors'].append("File must have an extension")
                validation_result['recovery_suggestions'].extend([
                    "Add a file extension (e.g., .mp3, .wav, .m4a)",
                    "Ensure your audio file has the correct extension"
                ])
                return validation_result
            
            # Validate file format
            if file_extension not in self.SUPPORTED_FORMATS:
                supported_formats = ', '.join(self.SUPPORTED_FORMATS.keys())
                validation_result['errors'].append(
                    f"Unsupported file format '{file_extension}'. Supported formats: {supported_formats}"
                )
                validation_result['recovery_suggestions'].extend([
                    f"Convert your file to one of these supported formats: {supported_formats}",
                    "Use audio conversion software like Audacity, FFmpeg, or online converters",
                    "Check that your file extension matches the actual file format"
                ])
                return validation_result
            
            # Check file size with detailed error handling
            try:
                file_data.seek(0, os.SEEK_END)
                file_size = file_data.tell()
                file_data.seek(0)
            except Exception as e:
                validation_result['errors'].append(f"Unable to read file size: {str(e)}")
                validation_result['recovery_suggestions'].extend([
                    "Ensure the file is not corrupted",
                    "Try uploading the file again",
                    "Check that the file is not currently being used by another application"
                ])
                return validation_result
            
            if file_size == 0:
                validation_result['errors'].append("File is empty (0 bytes)")
                validation_result['recovery_suggestions'].extend([
                    "Ensure the file contains audio data",
                    "Check that the file was not corrupted during transfer",
                    "Try re-recording or re-exporting the audio file"
                ])
                return validation_result
            
            if file_size > self.max_file_size:
                max_size_mb = self.max_file_size / (1024 * 1024)
                current_size_mb = file_size / (1024 * 1024)
                validation_result['errors'].append(
                    f"File too large ({current_size_mb:.1f}MB). Maximum size: {max_size_mb:.1f}MB"
                )
                validation_result['recovery_suggestions'].extend([
                    f"Compress your audio file to under {max_size_mb:.1f}MB",
                    "Use audio editing software to reduce file size",
                    "Consider using a lower bitrate or different compression format",
                    "Split large files into smaller segments"
                ])
                return validation_result
            
            # Validate MIME type using python-magic if available
            detected_mime = None
            mime_validation_failed = False
            
            if HAS_MAGIC:
                try:
                    file_data.seek(0)
                    file_content = file_data.read(min(1024, file_size))  # Read first 1KB or entire file if smaller
                    file_data.seek(0)
                    
                    detected_mime = magic.from_buffer(file_content, mime=True)
                    expected_mimes = self.SUPPORTED_FORMATS[file_extension]
                    
                    if detected_mime not in expected_mimes:
                        validation_result['warnings'].append(
                            f"File content type '{detected_mime}' doesn't match extension '{file_extension}'"
                        )
                        validation_result['recovery_suggestions'].append(
                            "Verify that your file extension matches the actual file format"
                        )
                        mime_validation_failed = True
                        
                except Exception as e:
                    self.logger.warning(f"MIME type detection failed: {e}")
                    validation_result['warnings'].append("Could not verify file content type")
                    validation_result['recovery_suggestions'].append(
                        "File content verification failed - proceed with caution"
                    )
            else:
                validation_result['warnings'].append("MIME type detection not available (python-magic not installed)")
            
            # Additional file integrity checks
            try:
                # Try to read a small portion of the file to check for corruption
                file_data.seek(0)
                test_chunk = file_data.read(min(4096, file_size))
                file_data.seek(0)
                
                if len(test_chunk) == 0 and file_size > 0:
                    validation_result['errors'].append("File appears to be corrupted - cannot read content")
                    validation_result['recovery_suggestions'].extend([
                        "The file may be corrupted during upload",
                        "Try uploading the file again",
                        "Verify the original file is not corrupted"
                    ])
                    return validation_result
                    
            except Exception as e:
                validation_result['warnings'].append(f"File integrity check failed: {str(e)}")
                validation_result['recovery_suggestions'].append("File may be corrupted - upload may fail")
            
            # Extract metadata
            validation_result['metadata'] = {
                'original_filename': original_filename,
                'secure_filename': filename,
                'file_extension': file_extension,
                'file_size': file_size,
                'file_size_mb': round(file_size / (1024 * 1024), 2),
                'mime_type': file_data.content_type,
                'detected_mime': detected_mime,
                'validation_timestamp': datetime.utcnow().isoformat(),
                'mime_validation_passed': not mime_validation_failed
            }
            
            # If no errors, mark as valid
            if not validation_result['errors']:
                validation_result['is_valid'] = True
                self.logger.info(f"File validation successful: {filename} ({file_size} bytes)")
                
                # Add success suggestions
                if validation_result['warnings']:
                    validation_result['recovery_suggestions'].append(
                        "File passed validation with warnings - upload should proceed normally"
                    )
            else:
                self.logger.warning(f"File validation failed for {filename}: {validation_result['errors']}")
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"File validation error: {e}")
            error_msg = f"File validation failed: {str(e)}"
            
            # Provide helpful error messages based on exception type
            if isinstance(e, PermissionError):
                error_msg += " - Permission denied"
                recovery_suggestions = [
                    "Check file permissions",
                    "Ensure the file is not locked by another application",
                    "Try copying the file to a different location first"
                ]
            elif isinstance(e, OSError):
                error_msg += " - System error"
                recovery_suggestions = [
                    "Check available disk space",
                    "Verify the file is not corrupted",
                    "Try uploading a different file to test the system"
                ]
            else:
                recovery_suggestions = [
                    "Try uploading the file again",
                    "Check that the file is a valid audio file",
                    "Contact support if the issue persists"
                ]
            
            raise ValidationError(error_msg, recovery_suggestions=recovery_suggestions)
    
    @retry_on_failure(max_retries=3, delay=0.5, backoff_factor=2.0)
    def save_temp_file(self, file_data: FileStorage) -> str:
        """
        Save file temporarily for processing with retry mechanism
        
        Args:
            file_data: Werkzeug FileStorage object
            
        Returns:
            Path to saved temporary file
            
        Raises:
            ProcessingError: If file saving fails
            FileOperationError: If file operations fail after retries
        """
        temp_file_path = None
        
        try:
            # Validate file first
            validation_result = self.validate_file(file_data)
            if not validation_result['is_valid']:
                error_msg = f"File validation failed: {', '.join(validation_result['errors'])}"
                raise ValidationError(
                    error_msg, 
                    recovery_suggestions=validation_result.get('recovery_suggestions', [])
                )
            
            metadata = validation_result['metadata']
            
            # Check available disk space
            self._check_disk_space(metadata['file_size'])
            
            # Generate unique filename
            unique_id = uuid.uuid4().hex
            file_extension = metadata['file_extension']
            temp_filename = f"upload_{unique_id}.{file_extension}"
            temp_file_path = os.path.join(self.temp_dir, temp_filename)
            
            # Ensure temp directory exists
            os.makedirs(self.temp_dir, exist_ok=True)
            
            # Save file with atomic operation
            temp_file_path_partial = f"{temp_file_path}.partial"
            
            try:
                file_data.seek(0)
                
                # Save to partial file first
                with open(temp_file_path_partial, 'wb') as temp_file:
                    # Copy in chunks to handle large files
                    chunk_size = 64 * 1024  # 64KB chunks
                    while True:
                        chunk = file_data.read(chunk_size)
                        if not chunk:
                            break
                        temp_file.write(chunk)
                        temp_file.flush()  # Ensure data is written
                        os.fsync(temp_file.fileno())  # Force write to disk
                
                # Verify partial file was saved correctly
                if not os.path.exists(temp_file_path_partial):
                    raise FileOperationError(
                        "Failed to create temporary file",
                        error_code="FILE_CREATION_FAILED",
                        retryable=True,
                        recovery_suggestions=[
                            "Check available disk space",
                            "Verify write permissions to temporary directory",
                            "Try uploading a smaller file"
                        ]
                    )
                
                saved_size = os.path.getsize(temp_file_path_partial)
                if saved_size != metadata['file_size']:
                    os.remove(temp_file_path_partial)
                    raise FileOperationError(
                        f"File size mismatch: expected {metadata['file_size']}, got {saved_size}",
                        error_code="SIZE_MISMATCH",
                        retryable=True,
                        recovery_suggestions=[
                            "The file may have been corrupted during upload",
                            "Try uploading the file again",
                            "Check your internet connection stability"
                        ]
                    )
                
                # Atomically move partial file to final location
                shutil.move(temp_file_path_partial, temp_file_path)
                
                # Log file details for debugging
                final_size = os.path.getsize(temp_file_path)
                self.logger.info(f"File saved successfully: {temp_file_path} ({final_size} bytes)")
                
                # Check file header for debugging
                with open(temp_file_path, 'rb') as f:
                    header = f.read(16)
                    self.logger.info(f"Saved file header: {header.hex()}")
                
                # Final verification
                if not os.path.exists(temp_file_path):
                    raise FileOperationError(
                        "File move operation failed",
                        error_code="MOVE_FAILED",
                        retryable=True,
                        recovery_suggestions=[
                            "Check file system permissions",
                            "Verify available disk space",
                            "Try uploading to a different location"
                        ]
                    )
                
                # Verify final file integrity
                final_size = os.path.getsize(temp_file_path)
                if final_size != metadata['file_size']:
                    os.remove(temp_file_path)
                    raise FileOperationError(
                        f"Final file verification failed: size mismatch",
                        error_code="FINAL_VERIFICATION_FAILED",
                        retryable=True,
                        recovery_suggestions=[
                            "File system may be corrupted",
                            "Try uploading to a different location",
                            "Check disk health"
                        ]
                    )
                
            except Exception as e:
                # Clean up partial file if it exists
                if os.path.exists(temp_file_path_partial):
                    try:
                        os.remove(temp_file_path_partial)
                    except:
                        pass
                raise e
            
            # Track file for cleanup
            with self._cleanup_lock:
                self._temp_files[temp_file_path] = {
                    'created_at': datetime.utcnow(),
                    'original_filename': metadata['original_filename'],
                    'file_size': metadata['file_size'],
                    'secure_filename': metadata['secure_filename'],
                    'file_extension': metadata['file_extension']
                }
            
            self.logger.info(f"Temporary file saved successfully: {temp_file_path}")
            return temp_file_path
            
        except (ValidationError, FileOperationError):
            # Clean up any partial files
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except:
                    pass
            raise
        except Exception as e:
            # Clean up any partial files
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except:
                    pass
                    
            self.logger.error(f"Error saving temporary file: {e}")
            
            # Provide specific error handling based on exception type
            if isinstance(e, PermissionError):
                raise FileOperationError(
                    f"Permission denied while saving file: {str(e)}",
                    error_code="PERMISSION_DENIED",
                    retryable=False,
                    recovery_suggestions=[
                        "Check write permissions to the upload directory",
                        "Ensure the application has sufficient privileges",
                        "Contact your system administrator"
                    ]
                )
            elif isinstance(e, OSError) and "No space left on device" in str(e):
                raise FileOperationError(
                    "Insufficient disk space to save file",
                    error_code="DISK_FULL",
                    retryable=False,
                    recovery_suggestions=[
                        "Free up disk space on the server",
                        "Try uploading a smaller file",
                        "Contact support to increase storage capacity"
                    ]
                )
            elif isinstance(e, OSError):
                raise FileOperationError(
                    f"System error while saving file: {str(e)}",
                    error_code="SYSTEM_ERROR",
                    retryable=True,
                    recovery_suggestions=[
                        "Check system resources and disk health",
                        "Try uploading the file again",
                        "Contact support if the issue persists"
                    ]
                )
            else:
                raise FileOperationError(
                    f"Failed to save temporary file: {str(e)}",
                    error_code="SAVE_FAILED",
                    retryable=True,
                    recovery_suggestions=[
                        "Try uploading the file again",
                        "Check that the file is not corrupted",
                        "Contact support if the issue persists"
                    ]
                )
    
    def _check_disk_space(self, required_bytes: int, safety_margin: float = 1.5):
        """
        Check if there's enough disk space for the file
        
        Args:
            required_bytes: Number of bytes needed
            safety_margin: Safety margin multiplier (default 1.5x)
        
        Raises:
            FileOperationError: If insufficient disk space
        """
        try:
            stat = shutil.disk_usage(self.temp_dir)
            available_bytes = stat.free
            required_with_margin = required_bytes * safety_margin
            
            if available_bytes < required_with_margin:
                available_mb = available_bytes / (1024 * 1024)
                required_mb = required_with_margin / (1024 * 1024)
                
                raise FileOperationError(
                    f"Insufficient disk space: {available_mb:.1f}MB available, {required_mb:.1f}MB required",
                    error_code="INSUFFICIENT_SPACE",
                    retryable=False,
                    recovery_suggestions=[
                        "Free up disk space on the server",
                        "Try uploading a smaller file",
                        "Contact support to increase storage capacity"
                    ]
                )
                
        except FileOperationError:
            raise
        except Exception as e:
            self.logger.warning(f"Could not check disk space: {e}")
            # Don't fail the operation if we can't check disk space
    
    @retry_on_failure(max_retries=2, delay=0.1, backoff_factor=2.0)
    def cleanup_temp_file(self, file_path: str) -> bool:
        """
        Clean up temporary file with retry mechanism
        
        Args:
            file_path: Path to temporary file
            
        Returns:
            True if cleanup successful, False otherwise
        """
        if not file_path:
            return True
            
        try:
            if os.path.exists(file_path):
                # Try to remove the file
                os.remove(file_path)
                self.logger.info(f"Temporary file cleaned up: {file_path}")
            else:
                self.logger.debug(f"Temporary file already removed: {file_path}")
            
            # Remove from tracking
            with self._cleanup_lock:
                file_info = self._temp_files.pop(file_path, None)
                if file_info:
                    self.logger.debug(f"Removed file from tracking: {file_info.get('original_filename', 'unknown')}")
            
            return True
            
        except PermissionError as e:
            self.logger.error(f"Permission denied cleaning up temporary file {file_path}: {e}")
            # Mark file for later cleanup
            with self._cleanup_lock:
                if file_path in self._temp_files:
                    self._temp_files[file_path]['cleanup_failed'] = True
                    self._temp_files[file_path]['cleanup_error'] = str(e)
            return False
            
        except OSError as e:
            self.logger.error(f"System error cleaning up temporary file {file_path}: {e}")
            # Mark file for later cleanup
            with self._cleanup_lock:
                if file_path in self._temp_files:
                    self._temp_files[file_path]['cleanup_failed'] = True
                    self._temp_files[file_path]['cleanup_error'] = str(e)
            return False
            
        except Exception as e:
            self.logger.error(f"Unexpected error cleaning up temporary file {file_path}: {e}")
            return False
    
    def force_cleanup_temp_file(self, file_path: str) -> bool:
        """
        Force cleanup of temporary file using multiple methods
        
        Args:
            file_path: Path to temporary file
            
        Returns:
            True if cleanup successful, False otherwise
        """
        if not file_path or not os.path.exists(file_path):
            return True
            
        cleanup_methods = [
            # Method 1: Standard removal
            lambda: os.remove(file_path),
            # Method 2: Change permissions then remove
            lambda: (os.chmod(file_path, 0o777), os.remove(file_path))[1],
            # Method 3: Move to temp then remove
            lambda: self._move_and_remove(file_path)
        ]
        
        for i, method in enumerate(cleanup_methods, 1):
            try:
                method()
                self.logger.info(f"Temporary file force cleaned up using method {i}: {file_path}")
                
                # Remove from tracking
                with self._cleanup_lock:
                    self._temp_files.pop(file_path, None)
                
                return True
                
            except Exception as e:
                self.logger.warning(f"Cleanup method {i} failed for {file_path}: {e}")
                continue
        
        self.logger.error(f"All cleanup methods failed for {file_path}")
        return False
    
    def _move_and_remove(self, file_path: str):
        """Helper method to move file to temp location then remove"""
        temp_name = f"{file_path}.delete_{uuid.uuid4().hex}"
        shutil.move(file_path, temp_name)
        os.remove(temp_name)
    
    def get_file_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from saved file
        
        Args:
            file_path: Path to file
            
        Returns:
            Dictionary containing file metadata
        """
        try:
            if not os.path.exists(file_path):
                raise ProcessingError(f"File not found: {file_path}")
            
            stat = os.stat(file_path)
            filename = os.path.basename(file_path)
            file_extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
            
            # Get MIME type
            mime_type = mimetypes.guess_type(file_path)[0]
            
            metadata = {
                'file_path': file_path,
                'filename': filename,
                'file_extension': file_extension,
                'file_size': stat.st_size,
                'file_size_mb': round(stat.st_size / (1024 * 1024), 2),
                'mime_type': mime_type,
                'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error extracting file metadata: {e}")
            raise ProcessingError(f"Failed to extract file metadata: {str(e)}")
    
    def create_upload_session(self, user_id: str, file_metadata: Dict[str, Any]) -> FileUploadSession:
        """
        Create a new file upload session
        
        Args:
            user_id: User identifier
            file_metadata: File metadata from validation
            
        Returns:
            FileUploadSession object
        """
        session_id = f"upload_{uuid.uuid4().hex}"
        
        session = FileUploadSession(
            session_id=session_id,
            user_id=user_id,
            original_filename=file_metadata['original_filename'],
            file_size=file_metadata['file_size'],
            file_format=file_metadata['file_extension']
        )
        
        session.update_status('uploaded')
        
        self.logger.info(f"Created upload session: {session_id}")
        return session
    
    def _start_cleanup_thread(self):
        """Start background thread for cleaning up old temporary files"""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(self.cleanup_interval)
                    self._cleanup_old_files()
                except Exception as e:
                    self.logger.error(f"Cleanup thread error: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
        self.logger.info("Cleanup thread started")
    
    def _cleanup_old_files(self):
        """Clean up temporary files older than cleanup interval"""
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.cleanup_interval)
        files_to_cleanup = []
        
        with self._cleanup_lock:
            for file_path, info in self._temp_files.items():
                if info['created_at'] < cutoff_time:
                    files_to_cleanup.append(file_path)
        
        for file_path in files_to_cleanup:
            self.cleanup_temp_file(file_path)
        
        if files_to_cleanup:
            self.logger.info(f"Cleaned up {len(files_to_cleanup)} old temporary files")
    
    def get_supported_formats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about supported file formats
        
        Returns:
            Dictionary with format information
        """
        format_info = {}
        for ext, mimes in self.SUPPORTED_FORMATS.items():
            format_info[ext] = {
                'extension': ext,
                'mime_types': mimes,
                'description': self._get_format_description(ext)
            }
        
        return format_info
    
    def _get_format_description(self, extension: str) -> str:
        """Get human-readable description for file format"""
        descriptions = {
            'mp3': 'MP3 Audio File',
            'wav': 'WAV Audio File',
            'm4a': 'M4A Audio File',
            'flac': 'FLAC Lossless Audio',
            'mp4': 'MP4 Audio/Video File',
            'wma': 'Windows Media Audio',
            'aac': 'AAC Audio File',
            'ogg': 'OGG Audio File'
        }
        return descriptions.get(extension, f'{extension.upper()} Audio File')