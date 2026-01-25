#!/usr/bin/env python3
"""
Conversational Turn Analyzer for Parent-Child Interactions.

Usage:
    python analyze.py audio.wav
    python analyze.py audio.mp3 --output results.json
    python analyze.py audio.wav --child-threshold 280 --response-threshold 2.5
"""

import argparse
import json
import sys
from pathlib import Path

from src.audio.loader import load_audio
from src.turn_detection.analyzer import ConversationAnalyzer


def main():
    parser = argparse.ArgumentParser(
        description="Analyze parent-child audio for conversational turns",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python analyze.py recording.wav
    python analyze.py recording.mp3 --output results.json
    python analyze.py recording.wav --child-threshold 280

Output:
    JSON with events (serve, return, missed_opportunity) and summary statistics.
        """,
    )

    parser.add_argument(
        "audio_file",
        type=str,
        help="Path to audio file (.wav or .mp3)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "--child-threshold",
        type=float,
        default=250.0,
        help="Pitch threshold for child classification in Hz (default: 250)",
    )
    parser.add_argument(
        "--response-threshold",
        type=float,
        default=3.0,
        help="Max seconds for response to count as return (default: 3.0)",
    )
    parser.add_argument(
        "--missed-threshold",
        type=float,
        default=5.0,
        help="Seconds of silence to count as missed opportunity (default: 5.0)",
    )
    parser.add_argument(
        "--vad-aggressiveness",
        type=int,
        default=2,
        choices=[0, 1, 2, 3],
        help="VAD aggressiveness 0-3 (default: 2, higher = more aggressive)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print progress information",
    )

    args = parser.parse_args()

    # Validate input file
    audio_path = Path(args.audio_file)
    if not audio_path.exists():
        print(f"Error: File not found: {args.audio_file}", file=sys.stderr)
        sys.exit(1)

    if audio_path.suffix.lower() not in (".wav", ".mp3", ".flac", ".ogg"):
        print(f"Error: Unsupported format: {audio_path.suffix}", file=sys.stderr)
        sys.exit(1)

    # Load audio
    if args.verbose:
        print(f"Loading audio: {args.audio_file}", file=sys.stderr)

    try:
        samples, sample_rate = load_audio(args.audio_file)
    except Exception as e:
        print(f"Error loading audio: {e}", file=sys.stderr)
        sys.exit(1)

    duration = len(samples) / sample_rate
    if args.verbose:
        print(f"Audio duration: {duration:.1f} seconds", file=sys.stderr)

    # Initialize analyzer
    analyzer = ConversationAnalyzer(
        sample_rate=sample_rate,
        response_threshold_sec=args.response_threshold,
        missed_threshold_sec=args.missed_threshold,
        child_pitch_threshold=args.child_threshold,
        vad_aggressiveness=args.vad_aggressiveness,
    )

    # Analyze
    if args.verbose:
        print("Analyzing...", file=sys.stderr)

    result = analyzer.analyze(samples)

    # Output
    json_output = result.to_json(indent=2)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(json_output)
        if args.verbose:
            print(f"Results written to: {args.output}", file=sys.stderr)
    else:
        print(json_output)

    # Print summary to stderr if verbose
    if args.verbose:
        summary = result.summary
        print(f"\n--- Summary ---", file=sys.stderr)
        print(f"Total serves (child): {summary.total_serves}", file=sys.stderr)
        print(f"Successful returns: {summary.total_returns}", file=sys.stderr)
        print(f"Missed opportunities: {summary.missed_opportunities}", file=sys.stderr)
        print(f"Success rate: {summary.successful_return_rate:.0%}", file=sys.stderr)
        if summary.average_response_latency:
            print(f"Avg response time: {summary.average_response_latency:.2f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
