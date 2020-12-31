all: flatbuffers cython
.PHONY: cython flatbuffers all clean

flatbuffers/Makefile:
	cd flatbuffers && cmake -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release

flatbuffers/flatc: flatbuffers/Makefile
	cd flatbuffers && $(MAKE)

flatbuffers: infinitd_server/battle.fbs flatbuffers/flatc
	flatbuffers/flatc --python --cpp --ts infinitd_server/battle.fbs --gen-object-api

cython:
	pipenv run python setup.py build_ext --inplace

clean:
	rm -rf build/ infinitd_server/cpp_battle_computer/battle_computer.cpp InfiniTDFb/ \
	infinitd_server/__pycache__/ flatbuffers/Makefile flatbuffers/flatc flatbuffers/CMakeCache.txt