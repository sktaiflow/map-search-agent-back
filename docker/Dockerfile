# Use the lightweight Python 3.12-slim image
FROM python:3.12-slim

# Set the working directory inside the container
WORKDIR /app

# Install dependencies needed for pip and system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc curl git && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements.txt and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ✅ Copy project code — for first build (will be overridden by volume mount in dev)
COPY . .

# Expose Jupyter port
EXPOSE 8888

# Set the default command to start Jupyter Notebook
CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]