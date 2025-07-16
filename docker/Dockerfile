# Use the lightweight Python 3.12-slim image
FROM python:3.12-slim
# Set the working directory inside the container
WORKDIR /app
# Install dependencies needed for pip and system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc && \
    rm -rf /var/lib/apt/lists/*
# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Set /bin/bash as the default command for interactive mode
#CMD ["/bin/bash"]
# Set the default command to start Jupyter Notebook
CMD ["jupyter", "notebook", "--ip='*'", "--port=8888", "--no-browser", "--allow-root"]