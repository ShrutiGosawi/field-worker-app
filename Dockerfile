# Use a clean, modern version of Python
FROM python:3.11-slim

# Set the active folder inside the container
WORKDIR /app

# Install the required packages directly inside the engine block
RUN pip install --no-cache-dir streamlit st-gsheets-connection pandas xlsxwriter openpyxl

# Copy the app code and the secure configurations folder inside
COPY app.py .
COPY .streamlit/ .streamlit/

# Open the port so workers can connect over Wi-Fi
EXPOSE 8501

# Command to run the application server
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
