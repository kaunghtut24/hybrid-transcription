"""
Utility functions for handling text chunking and context window management
"""

import re
from typing import List, Tuple, Dict

class TextChunker:
    def __init__(self, max_chunk_size: int = 8000):
        self.max_chunk_size = max_chunk_size

    def split_transcript(self, transcript: str) -> List[str]:
        """
        Split a transcript into manageable chunks while preserving speaker turns and context.
        """
        # First split by speaker turns
        turns = re.split(r'(?<=\n)(?=\w+:)', transcript)
        
        chunks = []
        current_chunk = []
        current_length = 0
        
        for turn in turns:
            turn = turn.strip()
            if not turn:
                continue
                
            turn_length = len(turn)
            
            # If this turn alone is bigger than max_chunk_size, split it
            if turn_length > self.max_chunk_size:
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # Split long turn into sentences
                sentences = re.split(r'(?<=[.!?])\s+', turn)
                sub_chunk = []
                sub_length = 0
                
                for sentence in sentences:
                    sentence_length = len(sentence)
                    if sub_length + sentence_length + 1 <= self.max_chunk_size:
                        sub_chunk.append(sentence)
                        sub_length += sentence_length + 1
                    else:
                        if sub_chunk:
                            chunks.append(' '.join(sub_chunk))
                        sub_chunk = [sentence]
                        sub_length = sentence_length
                
                if sub_chunk:
                    chunks.append(' '.join(sub_chunk))
                    
            # If adding this turn would exceed max_chunk_size, start a new chunk
            elif current_length + turn_length + 1 > self.max_chunk_size:
                chunks.append('\n'.join(current_chunk))
                current_chunk = [turn]
                current_length = turn_length
            else:
                current_chunk.append(turn)
                current_length += turn_length + 1
        
        # Add the last chunk if there is one
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks

    def merge_summaries(self, summaries: List[str]) -> str:
        """
        Merge multiple chunk summaries into a coherent final summary.
        """
        if len(summaries) == 1:
            return summaries[0]
            
        # Remove redundant information and merge summaries
        cleaned_summaries = []
        seen_points = set()
        
        for summary in summaries:
            # Split into bullet points if the summary uses them
            points = re.split(r'\n(?=[-•*]|\d+\.|\w+:)', summary)
            
            unique_points = []
            for point in points:
                point = point.strip('- •*').strip()
                # Create a normalized version for comparison
                normalized = re.sub(r'\s+', ' ', point.lower())
                if normalized not in seen_points and len(normalized) > 10:  # Ignore very short points
                    seen_points.add(normalized)
                    unique_points.append(point)
            
            if unique_points:
                cleaned_summaries.append('\n'.join(unique_points))
        
        # Combine all unique points
        final_summary = "Meeting Summary:\n\n" + \
                       "\n\n".join(cleaned_summaries)
        
        return final_summary

def count_tokens(text: str) -> int:
    """
    Estimate the number of tokens in a text.
    This is a rough estimation - actual token count may vary.
    """
    # Average English word is about 1.3 tokens
    words = len(text.split())
    return int(words * 1.3)
