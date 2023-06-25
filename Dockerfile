# set base image (host OS)
FROM python:3.8

# Install system dependencies for Bluetooth support
RUN apt-get update && apt-get install -y bluez

# set the working directory in the container
WORKDIR /code

# copy the dependencies file to the working directory
COPY requirements.txt .

# install Python dependencies
RUN pip install -r requirements.txt

# copy the content of the local src directory to the working directory
COPY . .

# command to run on container start
CMD [ "python", "run.py" ]
