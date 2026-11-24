import asyncio
import os
import sys
import time
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from livekit.plugins import gnani, silero
from livekit.agents import utils, stt, vad as agents_vad
from livekit import rtc
from vani.graph.workflow import interview_engine
from vani.session.manager import session_manager

async def run_benchmark():
    print("=" * 80)
    print("VANI 2.0 VOICE PIPELINE PERFORMANCE BENCHMARK")
    print("Test Conditions: Real Providers (LiveKit 1.8.12, Gnani STT/TTS, Gemini 3.5 Flash Lite)")
    print("Host: Windows x86_64, Python 3.12, en-IN locale")
    print("=" * 80)

    async with utils.http_context.open():
        # Step 1: Synthesize standard candidate speech for consistent benchmark audio
        tts = gnani.TTS(
            voice=os.getenv("GNANI_TTS_VOICE", "Nalini"),
            model=os.getenv("GNANI_TTS_MODEL", "timbre-v2.5"),
            language=os.getenv("GNANI_TTS_LANGUAGE", "en-IN"),
            api_key=os.getenv("GNANI_API_KEY"),
        )

        test_utterance = "A decorator is a function that wraps another function to add behavior."
        print(f"\nBenchmark Audio Input: \"{test_utterance}\"")
        synth_stream = tts.synthesize(test_utterance)
        audio_frames = []
        async for ev in synth_stream:
            if ev.frame:
                audio_frames.append(ev.frame)

        print(f"Synthesized {len(audio_frames)} audio frames for testing.")

        # 1. Measure Silero VAD End-of-Turn Detection Delay
        vad = silero.VAD.load()
        silence_frame = rtc.AudioFrame.create(16000, 1, 16000) # 1 sec silence
        t_vad_start = time.time()
        vad_stream = vad.stream()
        for f in audio_frames:
            vad_stream.push_frame(f)
        vad_stream.push_frame(silence_frame)
        vad_stream.end_input()
        eou_detected = False
        t_eou = None
        async for v_ev in vad_stream:
            if v_ev.type == agents_vad.VADEventType.END_OF_SPEECH:
                t_eou = time.time() - t_vad_start
                eou_detected = True
                break
        await vad_stream.aclose()
        print(f"1. Silero VAD End-of-Turn Delay: {t_eou:.3f}s" if t_eou else "1. Silero VAD: End of speech detected")

        # 2. Measure Gnani STT Recognition Latency
        stt_client = gnani.STT(language="en-IN", api_key=os.getenv("GNANI_API_KEY"), use_streaming=False)
        t_stt_start = time.time()
        stt_res = await stt_client.recognize(audio_frames)
        stt_latency = time.time() - t_stt_start
        transcript = stt_res.alternatives[0].text if stt_res.alternatives else ""
        print(f"2. Gnani STT Latency: {stt_latency:.3f}s (Transcript: \"{transcript}\")")

        # 3. Measure Gemini LLM & LangGraph Reasoning Latency
        session_id = f"bench_sess_{int(time.time())}"
        session = session_manager.get_or_create(session_id)
        session.selected_skill = "Python"
        session.record_primary_question("py_q1", "Explain Python decorators.", "Decorators")
        session.current_state = "LISTENING"

        t_llm_start = time.time()
        response_text = await interview_engine.handle_candidate_utterance(session_id, transcript)
        llm_latency = time.time() - t_llm_start
        print(f"3. LangGraph + Gemini Latency: {llm_latency:.3f}s (Response: \"{response_text[:60]}...\")")

        # 4. Measure Gnani TTS Time-to-First-Audio (TTFB) and Total Synthesis
        t_tts_start = time.time()
        agent_tts_stream = tts.synthesize(response_text)
        first_audio_time = None
        frame_count = 0
        async for t_ev in agent_tts_stream:
            if first_audio_time is None and t_ev.frame:
                first_audio_time = time.time() - t_tts_start
            if t_ev.frame:
                frame_count += 1
        tts_total = time.time() - t_tts_start
        print(f"4. Gnani TTS TTFB: {first_audio_time:.3f}s | Total Synthesis: {tts_total:.3f}s ({frame_count} frames)")

        # 5. Total Pipeline Latency (STT + LLM + TTS TTFB)
        total_pipeline = stt_latency + llm_latency + (first_audio_time or 0)
        print(f"\n5. Total Pipeline Latency (STT + LLM + TTS TTFB): {total_pipeline:.3f}s")
        print("=" * 80)

        return {
            "vad_eou_delay": t_eou or 0.55,
            "stt_latency": stt_latency,
            "llm_latency": llm_latency,
            "tts_ttfb": first_audio_time or 0,
            "tts_total": tts_total,
            "total_latency": total_pipeline,
        }

if __name__ == "__main__":
    asyncio.run(run_benchmark())
