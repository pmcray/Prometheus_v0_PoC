# Use an official NVIDIA L4T base image for Jetson
FROM nvcr.io/nvidia/l4t-jetpack:r36.2.0

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python and the dependencies from requirements.txt
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    pip3 install --no-cache-dir -r requirements.txt

# Add a label to indicate the purpose of this image
LABEL description="Development environment for Project Prometheus PoC on Jetson"

# By default, start a bash shell when the container runs.
# This allows for interactive testing and execution of scripts.
CMD ["/bin/bash"]
