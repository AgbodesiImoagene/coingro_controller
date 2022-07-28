FROM coingro:1.0.5

USER cguser

RUN mkdir /coingro_controller

WORKDIR /coingro_controller

# Install and execute
COPY --chown=cguser:cguser . /coingro_controller/

RUN pip install -e .[all] --user --no-cache-dir --no-build-isolation \
  && coingro create-userdir --userdir /coingro/user_data/

ENTRYPOINT ["coingro-controller"]
# Default to trade mode
CMD [ "start-controller" ]
