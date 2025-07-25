pip install -r requirements.txt
python setup_env.py
start /B uvicorn main:app --reload --host 0.0.0.0 --port 8000 --use-colors
start chrome https://localhost:8000