FROM python:3

# System deps for Fiona/GDAL/PROJ and a compiler toolchain
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin libgdal-dev proj-bin libproj-dev build-essential \
  && rm -rf /var/lib/apt/lists/*

# Make headers visible to pip builds
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal
# Also point explicitly to gdal-config
ENV GDAL_CONFIG=/usr/bin/gdal-config

# Copy requirements early for layer caching
COPY requirements.txt /requirements.txt

# Install numpy first to speed up dependent builds
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir numpy

# Keep GDAL Python bindings in lockstep with system GDAL
RUN GDAL_VERSION="$(gdal-config --version)" && \
    pip install --no-cache-dir "GDAL==${GDAL_VERSION}.*"

# Now install the rest
RUN pip install --no-cache-dir -r /requirements.txt

# App files
WORKDIR /app
COPY . /app

# Your existing bits
EXPOSE 9487
ENV PYTHONUNBUFFERED=1
RUN chmod 644 _server.py
CMD ["python", "-u", "_server.py"]



# FROM python:3
# # Make port 9487 available to the world outside this container
# EXPOSE 9487
# COPY requirements.txt /
# ENV PYTHONUNBUFFERED=1
# RUN pip install -r /requirements.txt
# #flask run from install file
# COPY . /app
# WORKDIR /app

# RUN chmod 644 _server.py

# CMD ["python", "-u", "_server.py"]