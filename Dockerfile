# Use the official NVIDIA L4T base image with JetPack
FROM nvcr.io/nvidia/l4t-jetpack:r35.2.1

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install Python and pip, then install the Python dependencies
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Set the default command to run the main script
CMD ["python3", "main.py"]