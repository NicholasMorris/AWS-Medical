#!/usr/bin/env python3
"""
Live transcription with AWS Transcribe (non-medical).
Region: ap-southeast-2

Ctrl+C will stop recording, close the stream, and allow final transcripts to be processed.
"""

import asyncio
import queue
import sys
import threading
import signal
from dataclasses import dataclass, field
from typing import Optional

import sounddevice as sd  # pip install sounddevice
from amazon_transcribe.client import TranscribeStreamingClient  # pip install amazon-transcribe
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent

# ---- Configuration ----
REGION = "ap-southeast-2"
LANGUAGE_CODE = "en-AU"           # choose your language (e.g. en-US / en-AU)
SAMPLE_RATE = 16000              # Transcribe streaming supports 8k/16k commonly
MEDIA_ENCODING = "pcm"           # 'pcm'
CHANNELS = 1                     # mono
CHUNK_MS = 100                   # how many ms per audio chunk we push
SAMPLE_WIDTH = 2                 # bytes per sample for int16 (16-bit PCM)
DEVICE = None                    # None = default input device; set index if you want a specific mic

# ---- Safe shutdown flag ----
stop_event = threading.Event()

# ---- Helpers ----
@dataclass
class TranscriptCollector(TranscriptResultStreamHandler):
    """Simple handler to collect and print transcript events."""
    output_stream: any = field(repr=False, default=None)
    final_text: str = ""
    partial_buffer: str = ""

    async def handle_transcript_event(self, event: TranscriptEvent):
        # Iterate through results & alternatives per event
        for result in event.transcript.results:
            # If result.is_partial is True -> interim result
            if getattr(result, "is_partial", False):
                # print interim
                if result.alternatives:
                    txt = result.alternatives[0].transcript
                    # overwrite partial buffer
                    self.partial_buffer = txt
                    print(f"\r[partial] {txt}", end="", flush=True)
            else:
                # Final result: add to final_text and clear partial
                if result.alternatives:
                    txt = result.alternatives[0].transcript
                    self.final_text += (txt + " ")
                    # move to new line for final
                    print(f"\r[final]   {txt}")
                    self.partial_buffer = ""
    
    async def handle_events(self):
        # default walker over the output_stream to process events
        async for event in self.output_stream:
            # delegate based on type
            if isinstance(event, TranscriptEvent):
                await self.handle_transcript_event(event)
            # other event types exist, ignore for this example

# ---- Microphone -> asyncio.Queue bridge ----
def start_microphone_stream(q: queue.Queue, sample_rate: int = SAMPLE_RATE, device: Optional[int] = DEVICE):
    """Start a blocking sounddevice InputStream in a background thread, pushing raw PCM16 bytes to q."""

    def callback(indata, frames, time, status):
        """sounddevice callback runs in a separate thread from the main thread."""
        if status:
            # print status warnings
            print(f"\n[device status] {status}", file=sys.stderr)
        # indata is a numpy array of shape (frames, channels) dtype=int16 if configured
        # convert to bytes (raw PCM16LE)
        q.put(bytes(indata.tobytes()))
    
    # Use RawInputStream to get raw bytes (dtype='int16') so we can send PCM16
    stream = sd.RawInputStream(
        samplerate=sample_rate,
        blocksize=int(sample_rate * CHUNK_MS / 1000),
        dtype="int16",
        channels=CHANNELS,
        callback=callback,
        device=device
    )
    stream.start()
    return stream

# ---- Async coroutine to read from queue and send audio events ----
async def audio_sender(stream, q: queue.Queue):
    """
    Read bytes from queue and send them to the Transcribe stream as audio events.
    `stream` is the object returned by client.start_stream_transcription(...)
    """
    try:
        print("\n[info] Starting audio sender coroutine.")
        while not stop_event.is_set():
            try:
                # wait for up to 0.5s for audio chunk
                chunk = q.get(timeout=0.5)
            except queue.Empty:
                continue
            # send audio chunk (PCM16 bytes)
            await stream.input_stream.send_audio_event(audio_chunk=chunk)
        # when stop event is set, end the audio stream
        print("\n[info] stop_event set; ending stream input.")
        await stream.input_stream.end_stream()
    except Exception as e:
        print(f"[error] audio_sender exception: {e}", file=sys.stderr)
        try:
            await stream.input_stream.end_stream()
        except Exception:
            pass

# ---- Main async function ----
async def transcribe_live():
    q = queue.Queue(maxsize=20)  # holds raw audio chunks from microphone

    # start microphone in background thread
    mic_stream = start_microphone_stream(q, sample_rate=SAMPLE_RATE, device=DEVICE)
    print(f"[info] Microphone stream started (rate={SAMPLE_RATE}Hz). Speak now. Press Ctrl+C to stop.")

    # create Transcribe Streaming client
    client = TranscribeStreamingClient(region=REGION)

    # start stream transcription
    stream = await client.start_stream_transcription(
        language_code=LANGUAGE_CODE,
        media_sample_rate_hz=SAMPLE_RATE,
        media_encoding=MEDIA_ENCODING,
        # If you want to enable partial results faster, adjust parameters per SDK docs
    )

    # instantiate handler to process output events
    handler = TranscriptCollector(stream.output_stream)

    # schedule sender and handler concurrently
    sender_task = asyncio.create_task(audio_sender(stream, q))
    handler_task = asyncio.create_task(handler.handle_events())

    # Wait for both tasks: sender will end when stop_event is set and end_stream called
    try:
        await asyncio.gather(sender_task, handler_task)
    except asyncio.CancelledError:
        pass
    finally:
        # ensure microphone stopped
        try:
            mic_stream.stop()
            mic_stream.close()
        except Exception:
            pass
        # attempt to close client gracefully
        try:
            await client.close()
        except Exception:
            pass
    # print summary
    print("\n[info] Final transcript:")
    print(handler.final_text.strip())
    return handler.final_text.strip()

# ---- Signal / KeyboardInterrupt handling ----
def register_signal_handlers(loop):
    """Register signal handler so Ctrl+C triggers a clean shutdown."""
    def _signal_handler(signum, frame):
        print("\n[info] Signal received, stopping...")
        stop_event.set()
    
    signal.signal(signal.SIGINT, _signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, _signal_handler)

# ---- Entrypoint ----
def main():
    loop = asyncio.get_event_loop()
    register_signal_handlers(loop)
    try:
        final_text = loop.run_until_complete(transcribe_live())
        print(f"\n[done] Transcription finished. Final text length: {len(final_text)} chars")
    except KeyboardInterrupt:
        # If KeyboardInterrupt propagates here, ensure we set stop flag
        stop_event.set()
        print("\n[info] KeyboardInterrupt — stopping...")
    except Exception as e:
        print(f"[error] Exception in main: {e}", file=sys.stderr)
    finally:
        # ensure event loop closed
        try:
            loop.stop()
        except Exception:
            pass

if __name__ == "__main__":
    main()
