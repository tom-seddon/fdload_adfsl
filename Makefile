##########################################################################
##########################################################################

ifeq ($(OS),Windows_NT)
PYTHON:=py -3
UNAME:=Windows_NT
TASS:=$(PWD)/bin/64tass.exe
else
UNAME:=$(shell uname -s)
PYTHON:=/usr/bin/python3
TASS:=64tass
endif

##########################################################################
##########################################################################

_V:=$(if $(VERBOSE),,@)

##########################################################################
##########################################################################

TASS_ARGS:=--case-sensitive -Wall --cbm-prg $(if $(VERBOSE),,--quiet) --long-branch --m65c02

##########################################################################
##########################################################################

PWD:=$(shell $(PYTHON) submodules/shellcmd.py/shellcmd.py realpath .)

# How to run shellcmd.py from any folder.
SHELLCMD:=$(PYTHON) $(PWD)/submodules/shellcmd.py/shellcmd.py

# submodules/beeb/bin (absolute path).
BEEB_BIN:=$(PWD)/submodules/beeb/bin

# Where intermediate build output goes (absolute path).
BUILD:=$(PWD)/build
DISK_CONTENTS:=$(BUILD)/disk

# Where the BeebLink volume lives.
BEEBLINK_VOLUME:=$(PWD)/beeb/adfsl_fixed_layout

# Where BBC build output goes.
BEEB_BUILD:=$(BEEBLINK_VOLUME)/Z

##########################################################################
##########################################################################

.PHONY: build
build: _output_folders
# Create the files list.
	$(_V)$(PYTHON) "bin/boot_builder.py" constants --output "$(BUILD)/files_list.generated.s65"

# Assemble stuff
	$(_V)$(MAKE) _asm PC=fdload BEEB=FDLOAD "TASS_EXTRA_ARGS=-Dinclude_test_hooks=true"
	$(_V)$(MAKE) _asm PC=loader0 BEEB=LOADER0
	$(_V)$(MAKE) _asm PC=loader1 BEEB=LOADER1

# Build the big file.
	$(_V)$(PYTHON) "bin/boot_builder.py" build --vdu21 --loader0 "$(BUILD)/loader0.prg" --loader1 "$(BUILD)/loader1.prg" --output-data "$(BUILD)/!boot.dat" --output-toc "$(BUILD)/!boot.toc.json"

# Form ADFS disk contents in $(DISK_CONTENTS): !BOOT and its .inf.
	$(_V)$(SHELLCMD) concat -o "$(DISK_CONTENTS)/!BOOT" --pad 653568 "$(BUILD)/!boot.dat"
	$(_V)echo "$$.!BOOT FFFFFFFF FFFFFFFF" > "$(DISK_CONTENTS)/!BOOT.inf"

# Create the ADFS disk image.
	$(_V)$(PYTHON) "$(BEEB_BIN)/adf_create.py" -o "$(BUILD)/adfsl_fixed_layout.adl" --opt4 3 --title "AMAZING DEMO" "$(DISK_CONTENTS)/!BOOT"

# Copy the ADFS disk image somewhere the BBC can see it too.
	$(_V)$(SHELLCMD) copy-file "$(BUILD)/adfsl_fixed_layout.adl" "$(BEEB_BUILD)/$$.ADFSL_DISK"

##########################################################################
##########################################################################

.PHONY: clean
clean:
	$(_V)$(SHELLCMD) rm-tree "$(BUILD)"
	$(_V)$(SHELLCMD) rm-tree "$(BEEB_BUILD)"

##########################################################################
##########################################################################

.PHONY: _output_folders
_output_folders:
	$(_V)$(SHELLCMD) mkdir "$(BUILD)"
	$(_V)$(SHELLCMD) mkdir "$(DISK_CONTENTS)"
	$(_V)$(SHELLCMD) mkdir "$(BEEB_BUILD)"

##########################################################################
##########################################################################

.PHONY: _asm
_asm:
	$(_V)$(TASS) $(TASS_ARGS) $(TASS_EXTRA_ARGS) -L "$(BUILD)/$(PC).lst" -l "$(BUILD)/$(PC).symbols" -o "$(BUILD)/$(PC).prg" "src/$(PC).s65"
	$(_V)$(PYTHON) "$(BEEB_BIN)/prg2bbc.py" $(PRG2BBC_EXTRA_ARGS) --io "$(BUILD)/$(PC).prg" "$(BEEB_BUILD)/$$.$(BEEB)"

##########################################################################
##########################################################################

.PHONY: _tom_emacs
_tom_emacs: _CONFIG:=MOS 3.50r + BeebLink
_tom_emacs: _DISK:=$(BUILD)/adfsl_fixed_layout.adl
_tom_emacs:
	$(_V)$(MAKE) build
	curl --connect-timeout 0.25 --silent -G 'http://localhost:48075/reset/b2' --data-urlencode "config=$(_CONFIG)"
	curl --connect-timeout 0.25 --silent -H 'Content-Type:application/binary' --upload-file '$(_DISK)' 'http://localhost:48075/mount/b2?drive=0&name=$(_DISK)'
