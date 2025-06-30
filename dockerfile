FROM ubuntu:22.04

# Install dependencies

RUN apt update

# Setup Localtime

RUN ln -fs /usr/share/zoneinfo/Europe/Madrid /etc/localtime

# Handling installation of the tzdata package separately as it is problematic

RUN DEBIAN_FRONTEND=noninteractive apt-get install -y tzdata

RUN apt install -y \
        g++ \
        python3 \
        python3-pip\
        cmake \
        ninja-build \
        git \
        ccache \
        gir1.2-goocanvas-2.0 \
        gir1.2-gtk-3.0 \
        python3-setuptools \
        qtbase5-dev \
        qtchooser \
        qt5-qmake \
        qtbase5-dev-tools \
        openmpi-bin \
        openmpi-common \
        openmpi-doc \
        libopenmpi-dev \
        mercurial \
        unzip \
        gdb \
        valgrind \
        libxml2 \
        libxml2-dev \
        libboost-all-dev \
        clang-format \
        doxygen \
        graphviz \
        imagemagick \
        texlive \
        texlive-extra-utils \
        texlive-latex-extra \
        texlive-font-utils \
        dvipng \
        latexmk \
        python3-sphinx \
        dia \
        gsl-bin \
        libgsl-dev \
        libgslcblas0 \
        tcpdump \
        sqlite \
        sqlite3 \
        libsqlite3-dev \
        libgtk-3-dev \
        vtun \
        lxc \
        uml-utilities




# Set working directory
WORKDIR /app

# source the venv environment in ./venv
RUN source ./venv/bin/activate

# changuing the working directory to /app/ns-3-dev
WORKDIR /app/ns-3-dev

# compile ns-3
RUN ./ns3 configure --enable-examples --enable-tests -d optimized
RUN ./ns3 build

# Uncomment to copy the necessary files to the container
# Not needed for now as this data is accessible through
# volumes declared in the top level docker compose

#COPY ./handover-simulator /app/handover-simulator
#COPY ./ns-3-dev /app/ns-3-dev
