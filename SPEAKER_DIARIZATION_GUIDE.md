# Speaker Diarization with Async Chunking - Implementation Guide

## Overview

This document describes the implementation of an advanced Speaker Diarization feature that combines AssemblyAI's speech-to-text API with Nvidia's NeMo TitaNet model for cross-clip speaker identification. This feature allows users to upload multiple audio clips and identify which speakers are the same across different recordings.

## Architecture

### Core Components

1. **SpeakerDiarizationService** (`services/speaker_diarization.py`)
   - Main service class handling the speaker diarization workflow
   - Integrates AssemblyAI for transcription and speaker labels
   - Uses NeMo TitaNet for advanced speaker verification
   - Manages async processing and progress tracking

2. **API Routes** (`app/routes/api/speaker_diarization.py`)
   - RESTful API endpoints for the feature
   - Handles file upload, processing, and results retrieval
   - Manages user sessions and progress tracking

3. **Frontend Interface** (`templates/speaker_diarization.html`)
   - Modern web interface for file upload and result display
   - Real-time progress tracking and error handling
   - Export functionality for results

## Key Features

### Advanced Speaker Identification
- **Cross-clip consistency**: Identifies the same speaker across multiple audio recordings
- **Voice embedding comparison**: Uses Nvidia's TitaNet model for acoustic similarity matching
- **Fallback mode**: Works with basic audio analysis when NeMo is not available

### Async Processing
- **Background processing**: Handles long-running tasks without blocking the UI
- **Progress tracking**: Real-time updates on processing status
- **Session management**: Maintains state across multiple requests

### Multiple Export Formats
- **JSON**: Complete data with metadata
- **CSV**: Structured data for analysis
- **Text**: Human-readable transcript

## Dependencies

### Required Dependencies
```
pydub==0.25.1          # Audio processing
numpy==1.24.3          # Numerical computations
assemblyai>=0.30.0     # Speech-to-text API
```

### Optional Dependencies (for enhanced functionality)
```
torch>=1.13.0              # PyTorch for NeMo
nemo-toolkit[all]==1.22.0  # Nvidia NeMo for speaker verification
```

### Installation Commands
```bash
# Install required dependencies
pip install pydub numpy

# Install optional dependencies for enhanced speaker verification
pip install torch nemo-toolkit[all]

# Or install all at once
pip install -r requirements.txt
```

## API Endpoints

### Service Information
```
GET /api/speaker-diarization/info
```
Returns service availability and capabilities.

### Upload Audio Chunks
```
POST /api/speaker-diarization/upload-chunks
Content-Type: multipart/form-data
Body: files[] (audio files)
```
Uploads multiple audio files for processing.

### Start Processing
```
POST /api/speaker-diarization/process/{session_id}
```
Starts speaker diarization processing.

### Check Status
```
GET /api/speaker-diarization/status/{session_id}
```
Returns processing status and progress.

### Get Results
```
GET /api/speaker-diarization/results/{session_id}
```
Returns detailed processing results.

### Export Results
```
GET /api/speaker-diarization/export/{session_id}?format={json|text|csv}
```
Exports results in specified format.

### Cleanup Session
```
DELETE /api/speaker-diarization/cleanup/{session_id}
```
Cleans up temporary files and session data.

## Usage Workflow

### 1. Service Validation
```javascript
const response = await fetch('/api/speaker-diarization/info');
const serviceInfo = await response.json();
console.log('Service available:', serviceInfo.available);
```

### 2. File Upload
```javascript
const formData = new FormData();
files.forEach(file => formData.append('files', file));

const uploadResponse = await fetch('/api/speaker-diarization/upload-chunks', {
    method: 'POST',
    body: formData
});
const uploadData = await uploadResponse.json();
const sessionId = uploadData.session_id;
```

### 3. Start Processing
```javascript
const processResponse = await fetch(`/api/speaker-diarization/process/${sessionId}`, {
    method: 'POST'
});
```

### 4. Monitor Progress
```javascript
const statusResponse = await fetch(`/api/speaker-diarization/status/${sessionId}`);
const status = await statusResponse.json();
console.log('Progress:', status.progress + '%');
```

### 5. Retrieve Results
```javascript
if (status.status === 'completed') {
    const resultsResponse = await fetch(`/api/speaker-diarization/results/${sessionId}`);
    const results = await resultsResponse.json();
    console.log('Unique speakers:', results.results.summary.unique_speakers_found);
}
```

## Configuration

### Environment Variables
```bash
# Required
ASSEMBLYAI_API_KEY=your_assemblyai_api_key

# Optional
UPLOAD_FOLDER=uploads                    # Directory for temporary files
MAX_CONTENT_LENGTH=104857600            # Max file size (100MB)
```

### Service Configuration
```python
# Create service instance
from services.speaker_diarization import create_speaker_diarization_service

service = create_speaker_diarization_service(
    api_key="your_assemblyai_key",
    config={
        'max_file_size': 100 * 1024 * 1024,  # 100MB
        'supported_formats': ['.wav', '.mp3', '.m4a', '.flac'],
        'max_clips': 10
    }
)
```

## Processing Workflow

### 1. File Upload and Validation
- Validates file formats and sizes
- Creates temporary storage directory
- Returns session ID for tracking

### 2. AssemblyAI Transcription
- Uploads files to AssemblyAI
- Starts transcription with speaker labels enabled
- Polls for completion

### 3. Speaker Analysis
- Extracts longest monologues for each speaker
- Creates audio clips for voice comparison
- Uses NeMo TitaNet for speaker verification (if available)

### 4. Speaker Mapping
- Compares new speakers against previous clips
- Creates unified speaker labels across clips
- Updates utterances with consistent speaker IDs

### 5. Results Generation
- Compiles speaker statistics
- Formats transcript with unified labels
- Prepares export data

## Advanced Features

### NeMo TitaNet Integration
```python
# Automatic model loading
speaker_model = nemo_asr.models.EncDecSpeakerLabelModel.from_pretrained(
    "nvidia/speakerverification_en_titanet_large"
)

# Speaker verification
verification_score = speaker_model.verify_speakers(clip1, clip2)
is_same_speaker = verification_score > 0.5
```

### Fallback Speaker Comparison
When NeMo is not available, the service uses basic audio analysis:
- Duration similarity comparison
- Energy level analysis
- Basic spectral similarity using FFT

### Progress Tracking
```python
def progress_callback(progress_data):
    session_data['progress'] = progress_data.get('progress', 0)
    session_data['current_stage'] = progress_data.get('stage', 'unknown')
    session_data['current_message'] = progress_data.get('message', '')
```

## Error Handling

### Common Error Scenarios
1. **Missing Dependencies**: Graceful degradation when NeMo is not available
2. **File Validation Errors**: Clear error messages for unsupported formats
3. **API Rate Limits**: Retry mechanisms with exponential backoff
4. **Processing Failures**: Detailed error reporting and recovery suggestions

### Error Response Format
```json
{
    "error": "Error description",
    "error_code": "ERROR_CODE",
    "troubleshooting": [
        "Suggestion 1",
        "Suggestion 2"
    ],
    "recovery_suggestions": [
        "Recovery action 1",
        "Recovery action 2"
    ]
}
```

## Performance Considerations

### File Size Limits
- Maximum 10 audio clips per session
- Maximum 100MB per file
- Recommended clip duration: 2-5 minutes

### Processing Time Estimates
- Upload: ~30 seconds per 100MB
- Transcription: ~20% of audio duration
- Speaker analysis: ~10% of audio duration
- Total: ~30-50% of total audio duration

### Memory Usage
- NeMo model: ~1-2GB GPU memory
- Audio processing: ~50MB per minute of audio
- Temporary files: ~2x original file size

## Security Considerations

### File Handling
- Secure filename generation
- Temporary file cleanup
- Size and format validation

### Session Management
- User-specific session isolation
- Automatic session cleanup
- Session expiration handling

### API Security
- Session-based authentication
- Rate limiting considerations
- Input validation and sanitization

## Testing

### Unit Tests
```python
# Test file validation
def test_validate_file():
    service = create_speaker_diarization_service(api_key)
    result = service.validate_file_for_transcription('test.wav')
    assert result['valid'] == True

# Test speaker comparison
def test_speaker_comparison():
    service = create_speaker_diarization_service(api_key)
    same_speaker = service.compare_embeddings('clip1.wav', 'clip2.wav')
    assert isinstance(same_speaker, bool)
```

### Integration Tests
```python
# Test complete workflow
async def test_complete_workflow():
    service = create_speaker_diarization_service(api_key)
    files = ['clip1.wav', 'clip2.wav', 'clip3.wav']
    results = await service.process_clips_async(transcript_ids, files)
    assert results['success'] == True
    assert len(results['unique_speakers']) > 0
```

## Deployment Notes

### Production Considerations
1. **Dependency Management**: Ensure all optional dependencies are installed
2. **Storage**: Configure persistent storage for temporary files
3. **Scaling**: Consider background task queues (Celery) for processing
4. **Monitoring**: Implement logging and error tracking

### Docker Deployment
```dockerfile
# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt
```

### Environment Setup
```bash
# Create upload directory
mkdir -p uploads
chmod 755 uploads

# Set environment variables
export ASSEMBLYAI_API_KEY=your_key
export UPLOAD_FOLDER=uploads
export MAX_CONTENT_LENGTH=104857600
```

## Troubleshooting

### Common Issues

1. **NeMo Installation Fails**
   ```bash
   # Try installing with specific PyTorch version
   pip install torch==1.13.0
   pip install nemo-toolkit[all]==1.22.0
   ```

2. **FFmpeg Not Found**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install ffmpeg
   
   # macOS
   brew install ffmpeg
   
   # Windows
   # Download from https://ffmpeg.org/download.html
   ```

3. **Out of Memory Errors**
   - Reduce the number of concurrent clips
   - Use smaller audio files
   - Ensure sufficient GPU memory for NeMo

4. **Slow Processing**
   - Check internet connection for AssemblyAI API calls
   - Verify GPU availability for NeMo
   - Consider preprocessing audio files (format conversion)

### Debug Mode
```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Create service with debug config
service = create_speaker_diarization_service(
    api_key,
    config={'debug': True}
)
```

## Future Enhancements

### Planned Features
1. **Real-time Processing**: Live audio stream processing
2. **Speaker Enrollment**: Pre-register known speakers
3. **Multi-language Support**: Enhanced language detection
4. **Advanced Analytics**: Speaker emotion and sentiment analysis
5. **Integration**: Webhook support for external systems

### Performance Improvements
1. **Caching**: Speaker embeddings cache
2. **Parallel Processing**: Concurrent clip processing
3. **GPU Optimization**: Better GPU memory management
4. **Compression**: Audio compression for faster upload

## Support and Documentation

### Resources
- [AssemblyAI Documentation](https://www.assemblyai.com/docs/)
- [NeMo Toolkit Documentation](https://docs.nvidia.com/deeplearning/nemo/user-guide/docs/en/stable/)
- [PyDub Documentation](https://pydub.com/)

### Contact
For technical support and feature requests, please refer to the project's issue tracker or documentation.
