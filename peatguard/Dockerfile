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

# Install SNAPHU from ISCE2 bundled source
RUN SNAPHU_DIR=$(find /opt/conda -name "snaphu" -path "*/contrib/*" -type d 2>/dev/null | head -1) \
    && if [ -n "$SNAPHU_DIR" ] && [ -d "$SNAPHU_DIR/src" ]; then \
         cd "$SNAPHU_DIR/src" && make && cp ../bin/snaphu /usr/local/bin/; \
       else \
         echo "SNAPHU not found in ISCE2 contrib, installing via pip" \
         && pip install --no-cache-dir snaphu; \
       fi

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
    "google-cloud-run>=0.10.0" \
    "cdsapi>=0.6.0" \
    "pyaps3>=0.3.0"

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

# CDS API key for ERA5 tropospheric correction (injected at runtime via env vars).
# The entrypoint script writes ~/.cdsapirc from CDS_API_URL + CDS_API_KEY if set.
RUN printf '#!/bin/sh\n\
if [ -n "$CDS_API_KEY" ]; then\n\
  echo "url: ${CDS_API_URL:-https://cds.climate.copernicus.eu/api}" > ~/.cdsapirc\n\
  echo "key: ${CDS_API_KEY}" >> ~/.cdsapirc\n\
fi\n\
exec "$@"\n' > /entrypoint.sh && chmod +x /entrypoint.sh

# Default working directory for processing
WORKDIR /workspace

ENTRYPOINT ["/entrypoint.sh", "peatguard"]
CMD ["--help"]
