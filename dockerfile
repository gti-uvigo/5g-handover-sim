FROM ubuntu:24.04

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
        python3-venv \
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
        sqlite3 \
        libsqlite3-dev \
        libgtk-3-dev \
        vtun \
        lxc \
        uml-utilities\
        python3-pip 


COPY . /app/

# Set working directory
WORKDIR /app


# Install Python dependencies
# Ubuntu 24.04 ships an externally managed Python (PEP 668), so the dependencies
# are installed in a virtualenv that is put first in the PATH
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# # clone the ns-3-dev repository
RUN git clone https://gitlab.com/nsnam/ns-3-dev.git
# checkout the specific version of ns-3-dev (3.48)
RUN cd ns-3-dev && git checkout ns-3.48
# change the working directory contrib/
WORKDIR /app/ns-3-dev/contrib
# Install 5G-LENA
RUN git clone https://gitlab.com/cttc-lena/nr.git
# checkout the specific version of 5G-LENA (v5.1, compatible with ns-3.48)
RUN cd nr && git checkout v5.1
# create a symbolic link from /app/network-simulator to /app/ns-3-dev/scratch
RUN ln -s /app/network-simulator /app/ns-3-dev/scratch/network-simulator


# # changing the working directory to /app/ns-3-dev
WORKDIR /app/ns-3-dev

# # compile ns-3
# The 5G-LENA translation units are memory hungry, so the number of parallel
# compilation jobs is limited to keep the build inside the Docker memory limit.
# Raise it with --build-arg NS3_BUILD_JOBS=<n> if the Docker VM has more RAM.
ARG NS3_BUILD_JOBS=4
RUN ./ns3 configure --enable-examples --enable-tests -d optimized
RUN ./ns3 build -j ${NS3_BUILD_JOBS}
