MANPAGESPATH := /usr/share/man
SHELL := /bin/bash
RST2MAN := rst2man
RSTFILES := $(shell find . -name '*.rst') 
TARGETS := $(shell find . -name '*.rst' | sed 's|./\(.*\).rst|\1|')

ifeq (, $(shell which $(RST2MAN)))
	$(error "No $(RST2MAN) in $(PATH).")
endif

.PHONY : all

% : 
	$(RST2MAN) $@.rst | gzip > $@.gz

all : $(TARGETS)

install :
	set -e; \
	for TARGET in $(TARGETS) ; do \
		MANNAME=$${TARGET%.*}; \
		MANSECT=$${TARGET#*.}; \
		MANFILEGZIP="$${TARGET}.gz"; \
		install -m 0644 $${MANFILEGZIP} $(MANPAGESPATH)/man$${MANSECT}/$${MANFILEGZIP}; \
	done

clean:
	rm -rf ./*.gz
