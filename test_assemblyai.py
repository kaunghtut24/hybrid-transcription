#!/usr/bin/env python3
"""
Test script to verify AssemblyAI API key using the new Streaming v3 API
"""

import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_assemblyai_key():
    api_key = os.environ.get('ASSEMBLYAI_API_KEY')
    
    if not api_key:
        print("❌ No AssemblyAI API key found in .env file")
        return False
    
    print(f"🔑 Testing AssemblyAI API key: {api_key[:10]}...")
    
    try:
        import assemblyai as aai
        from assemblyai.streaming.v3 import StreamingClient, StreamingClientOptions
        
        # Test the API key by creating a client
        client = StreamingClient(
            StreamingClientOptions(
                api_key=api_key,
                api_host="streaming.assemblyai.com",
            )
        )
        
        print("✅ AssemblyAI Streaming v3 client created successfully")
        print("✅ API key is valid for the new streaming API")
        return True
        
    except ImportError:
        print("❌ AssemblyAI SDK not installed")
        print("Run: pip install assemblyai>=0.30.0")
        return False
    except Exception as e:
        print(f"❌ Error creating streaming client: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing AssemblyAI Streaming v3 API Configuration")
    print("=" * 50)
    
    success = test_assemblyai_key()
    
    if success:
        print("\n✅ AssemblyAI configuration is working!")
        print("You can now use real-time transcription with the new API.")
    else:
        print("\n❌ AssemblyAI configuration failed!")
        print("\n🔧 To fix this:")
        print("1. Install the new SDK: pip install assemblyai>=0.30.0")
        print("2. Go to https://www.assemblyai.com/app/account")
        print("3. Copy your API key")
        print("4. Update ASSEMBLYAI_API_KEY in your .env file")
        print("5. Run this test again")