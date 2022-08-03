FROM coingro:1.0.9

USER root

RUN mkdir /coingro_controller \
  && chown cguser:cguser /coingro_controller

USER cguser
WORKDIR /coingro_controller

USER cguser
# Install and execute
COPY --chown=cguser:cguser . /coingro_controller/

RUN pip install -e .[all] --user --no-cache-dir --no-build-isolation

ENTRYPOINT ["coingro-controller"]
# Default to trade mode
CMD ["start"]
