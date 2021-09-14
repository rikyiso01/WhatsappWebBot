FROM ubuntu

WORKDIR /app

RUN apt update
RUN DEBIAN_FRONTEND=noninteractive apt install -y --no-install-recommends xvfb xserver-xephyr
RUN DEBIAN_FRONTEND=noninteractive apt install -y --no-install-recommends software-properties-common pipenv &&\
    add-apt-repository -y ppa:deadsnakes/ppa &&\
    DEBIAN_FRONTEND=noninteractive apt install -y --no-install-recommends python3.9
RUN DEBIAN_FRONTEND=noninteractive apt install -y --no-install-recommends curl unzip
RUN curl -o chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb &&\
    DEBIAN_FRONTEND=noninteractive apt install -y --no-install-recommends ./chrome.deb &&\
    rm chrome.deb
RUN curl -o chromedriver.zip https://chromedriver.storage.googleapis.com/`curl -s https://chromedriver.storage.googleapis.com/LATEST_RELEASE`/chromedriver_linux64.zip &&\
    unzip chromedriver.zip &&\
    rm chromedriver.zip &&\
    mv chromedriver /bin

COPY . .

RUN pipenv install --deploy --ignore-pipfile

ENTRYPOINT ["pipenv","run","python3.9","main.py"]
