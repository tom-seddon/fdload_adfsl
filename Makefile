##########################################################################
##########################################################################

ifeq ($(OS),Windows_NT)
PYTHON:=py -3
UNAME:=Windows_NT
else
UNAME:=$(shell uname -s)
PYTHON:=/usr/bin/python3
endif

##########################################################################
##########################################################################

_V:=$(if $(VERBOSE),,@)

##########################################################################
##########################################################################

PWD:=$(shell $(PYTHON) submodules/shellcmd.py/shellcmd.py realpath .)

# How to run shellcmd.py from any folder.
SHELLCMD:=$(PYTHON) $(PWD)/submodules/shellcmd.py/shellcmd.py

# submodules/beeb/bin (absolute path).
BEEB_BIN:=$(PWD)/submodules/beeb/bin

# Where intermediate build output goes (absolute path).
BUILD:=$(PWD)/build

##########################################################################
##########################################################################

.PHONY: build
build: _output_folders

.PHONY: clean
clean:
	$(_V)$(SHELLCMD) rm-tree "$(BUILD)"

##########################################################################
##########################################################################

.PHONY: _output_folders
_output_folders:
	$(_V)$(SHELLCMD) mkdir "$(BUILD)"

##########################################################################
##########################################################################
