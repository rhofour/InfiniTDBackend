all: flatbuffers cython
.PHONY: cython flatbuffers all

flatbuffers: infinitd_server/battle.fbs
	flatc --python infinitd_server/battle.fbs

cython:
	python setup.py build_ext --inplace
