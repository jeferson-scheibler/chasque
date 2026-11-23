FROM python:3.12-slim
# a imagem slim descarta /usr/share/doc; as configurações de exemplo do tilemaker moram lá
RUN echo 'path-include /usr/share/doc/tilemaker/*' > /etc/dpkg/dpkg.cfg.d/tilemaker \
    && apt-get update && apt-get install -y --no-install-recommends librsvg2-bin osmium-tool tilemaker potrace \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir fonttools brotli pillow numpy scipy
