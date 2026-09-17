FROM jenkins/jenkins:lts

USER root
RUN apt-get update \
	&& apt-get install -y --no-install-recommends ca-certificates nodejs npm \
	&& apt-get clean \
	&& rm -rf /var/lib/apt/lists/*


USER jenkins