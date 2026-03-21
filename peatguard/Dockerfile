# PeatGuard Pipeline Container
# Uses mambaforge for Python 3.10 + ISCE2 via conda-forge + MintPy + SNAPHU

FROM condaforge/mambaforge:latest AS base

# System dependencies for SNAPHU compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install ISCE2, MintPy, and geospatial stack via conda-forge
RUN mamba install -y -c conda-forge \
    python=3.10 \
    isce2 \
    mintpy \
    rasterio \
    geopandas \
    scikit-image \
    h5py \
    pyproj \
    gdal \
    && mamba clean -afy

# Install SNAPHU from source
RUN wget -q https://web.stanford.edu/group/radar/softwareandlinks/sw/snaphu/snaphu-v2.0.6.tar.gz \
    && tar xzf snaphu-v2.0.6.tar.gz \
    && cd snaphu-v2.0.6/src \
    && make \
    && cp ../bin/snaphu /usr/local/bin/ \
    && cd / \
    && rm -rf snaphu-v2.0.6*

# Python-only dependencies (not in conda-forge or need specific versions)
RUN pip install --no-cache-dir \
    "asf_search>=7.0.0" \
    "earthaccess>=0.9.0" \
    "pydantic>=2.5.0" \
    "pydantic-settings>=2.1.0" \
    "pyyaml>=6.0" \
    "click>=8.1.0" \
    "tqdm>=4.66.0" \
    "google-cloud-storage>=2.14.0" \
    "google-cloud-run>=0.10.0"

# Set PROJ and ISCE2 environment variables
ENV PROJ_LIB=/opt/conda/share/proj
ENV PROJ_DATA=/opt/conda/share/proj
ENV ISCE_HOME=/opt/conda/lib/python3.10/site-packages/isce
ENV PATH="${ISCE_HOME}/bin:${ISCE_HOME}/applications:${PATH}"

# Patch ISCE2 runTopo.py: fix IndexError when only 1 swath has valid bursts.
# boxes array is 1D (shape (4,)) instead of 2D (shape (N,4)) for single-swath.
RUN TOPO_FILE="${ISCE_HOME}/components/isceobj/TopsProc/runTopo.py" && \
    sed -i 's/bbox = \[np.min(boxes\[:,0\]), np.max(boxes\[:,1\]), np.min(boxes\[:,2\]), np.max(boxes\[:,3\])\]/boxes = np.atleast_2d(boxes); bbox = [np.min(boxes[:,0]), np.max(boxes[:,1]), np.min(boxes[:,2]), np.max(boxes[:,3])]/' "$TOPO_FILE"

# Install peatguard
COPY . /app
WORKDIR /app
RUN pip install --no-cache-dir .

# Default working directory for processing
WORKDIR /workspace

ENTRYPOINT ["peatguard"]
CMD ["--help"]
