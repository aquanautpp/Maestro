#!/bin/bash
cd algorithm
pip install -r requirements.txt
gunicorn realtime_detector:app --bind 0.0.0.0:${PORT:-5000}