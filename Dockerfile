FROM registry.fedoraproject.org/fedora:latest

COPY . .

RUN sudo dnf -y install \
        systemd-devel \
        json-c-devel \
        libcurl-devel \
        autoconf \
	automake \
	libtool \
	make \
	rpm-build

RUN autoreconf -if

RUN ./configure --disable-dependency-tracking --disable-silent-rules --prefix=/usr --sysconfdir=/etc
RUN sudo make install
RUN src/tlitest/tlitest-setup

CMD src/tlitest/tlitest-run -k play_from_file
