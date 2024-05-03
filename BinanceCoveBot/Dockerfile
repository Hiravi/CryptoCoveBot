# Base image
FROM python:3.11.9

# Working directory
WORKDIR /app

# Copy your Python file
COPY ./* /app

# Install dependencies (if needed)
RUN pip install -r requirements.txt

# Command to run
CMD ["python", "main.py"]
