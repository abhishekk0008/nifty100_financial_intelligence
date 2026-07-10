install:
	pip install -r requirements.txt

run:
	streamlit run app.py

test:
	pytest

format:
	black .

lint:
	ruff check .

clean:
	del /Q *.pyc
