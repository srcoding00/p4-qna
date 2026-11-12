FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

# This application does not use Yarn. Remove its optional APT source before
# devcontainer features run apt-get update; leave signature verification enabled.
RUN rm -f /etc/apt/sources.list.d/yarn.list \
          /etc/apt/sources.list.d/yarn.sources
