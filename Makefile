all: flatbuffers cython
.PHONY: cython flatbuffers all

flatbuffers/Makefile:
	cd flatbuffers && cmake -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release

flatbuffers/flatc: flatbuffers/Makefile
	cd flatbuffers && $(MAKE)

flatbuffers: infinitd_server/battle.fbs flatbuffers/flatc
	flatbuffers/flatc --python --cpp --ts infinitd_server/battle.fbs --gen-object-api

cython:
	python setup.py build_ext --inplace
