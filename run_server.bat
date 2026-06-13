@echo off
echo Starting Liar's Deck Server...
cd /d %~dp0
python server\main_server.py
pause
