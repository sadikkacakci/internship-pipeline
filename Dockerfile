FROM python:3.10-slim

# Set environment variables for non-interactive mode.
ENV DEBIAN_FRONTEND=noninteractive

COPY requirements.txt .
# Install necessary dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl htop net-tools cron && \
    rm -rf /var/lib/apt/lists/*
# Install pip requirements
RUN pip install --upgrade pip && python -m pip install -r requirements.txt


WORKDIR /app
COPY . /app

# Set the system timezone to Europe/Istanbul.
RUN ln -snf /usr/share/zoneinfo/Europe/Istanbul /etc/localtime && echo "Europe/Istanbul" > /etc/timezone

# Schedule the script to run once a day using cron
RUN echo "0 0 * * * /usr/local/bin/python /app/runner.py >> /proc/1/fd/1 2>>/proc/1/fd/2" > /etc/cron.d/runner

RUN chmod 0644 /etc/cron.d/runner
RUN crontab /etc/cron.d/runner

# Start cron
CMD ["cron", "-f"]
