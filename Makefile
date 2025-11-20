#MAKEFLAGS+=--no-print-directory

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

ifeq ($(UNAME),Darwin)
GNU_MAKE:=gmake --no-print-directory
else
GNU_MAKE:=$(MAKE)
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

# Where the BeebLink volume lives.
BEEBLINK_VOLUME:=$(PWD)/beeb/adfsl_fixed_layout

# Where BBC build output goes.
BEEB_BUILD:=$(BEEBLINK_VOLUME)/Z

# ZX02 stuff.
ZX02_PATH:=$(PWD)/submodules/zx02
ifeq ($(UNAME),Windows_NT)
$(error TODO: zx02...)
else
ZX02:=$(ZX02_PATH)/build/zx02
endif

# I just don't seem to be able to decide how I want this to work.
export ZX02PACK_ZX02=$(ZX02)
export ZX02PACK_CACHE=$(BUILD)/zx02_cache
BUILDER_ZX02PACK_ARGS:=--zx02pack-zx02 "$(ZX02PACK_ZX02)" --zx02pack-cache "$(ZX02PACK_CACHE)"

##########################################################################
##########################################################################

TEST_DISK_LIST_PY:=bin/test_disk_files.py
TEST_DISK_INTERMEDIATES:=$(BUILD)/test_disk/intermediates
TEST_DISK_CONTENTS:=$(BUILD)/test_disk/contents
TEST_DISK_BUILDER_ARGS:=--list "$(TEST_DISK_LIST_PY)" --intermediate-folder "$(TEST_DISK_INTERMEDIATES)" $(BUILDER_ZX02PACK_ARGS)
TEST_DISK_BEEBLINK_DRIVE:=Y

##########################################################################
##########################################################################

define newline


endef

##########################################################################
##########################################################################

.PHONY: build
build: _output_folders $(BUILD)/GhoulsRevenge.bbc.dat $(BUILD)/TitleScreen_BBC.bbc.dat
# Build prerequisites.
ifneq ($(UNAME),Windows_NT)
	$(_V)test -f "$(ZX02)" || (cd "$(ZX02_PATH)" && $(GNU_MAKE) all)
endif

# Create the files list.
	$(_V)$(PYTHON) "bin/boot_builder.py" $(TEST_DISK_BUILDER_ARGS) prepare --output-asm "$(BUILD)/test_disk_files.generated.s65"

#	$(_V)$(MAKE) _pack_test_files

# Assemble stuff
	$(_V)$(MAKE) _asm PC=loader0 BEEB=LOADER0
	$(_V)$(MAKE) _asm PC=loader1 BEEB=LOADER1

# Build the big file.
	$(_V)$(PYTHON) "bin/boot_builder.py" $(TEST_DISK_BUILDER_ARGS) build --vdu21 --loader0 "$(BUILD)/loader0.prg" --loader1 "$(BUILD)/loader1.prg"
#--output-beeblink "$(BEEB_FDLOAD_FILES)"

# Assemble a version of the fdload code that's vaguely testable from
# BASIC.
	$(_V)$(MAKE) _asm PC=fdload BEEB=FDLOAD "TASS_EXTRA_ARGS=-Dtest_build=true"

	$(_V)$(MAKE) _adfs_image "BOOT=$(TEST_DISK_INTERMEDIATES)/boot.dat" "DISK_CONTENTS=$(TEST_DISK_CONTENTS)" "PC_IMAGE=test_disk.adl" "BBC_IMAGE=TEST"

##########################################################################
##########################################################################

$(BUILD)/GhoulsRevenge.bbc.dat : data/GhoulsRevenge.png
	$(_V)$(PYTHON) "$(BEEB_BIN)/png2bbc.py" -o "$@" "$<" 2

$(BUILD)/TitleScreen_BBC.bbc.dat : data/TitleScreen_BBC.png
	$(_V)$(PYTHON) "$(BEEB_BIN)/png2bbc.py" -o "$@" "$<" 2 --160

##########################################################################
##########################################################################

# .PHONY:_pack_test_files
# _pack_test_files: _ZX02_TEST_FILES:=$(wildcard $(ZX02_PATH)/tests/files/*)
# _pack_test_files:
# 	$(foreach INDEX,0 1 2 3 4 5 6 7 8 9,$(_V)$(PYTHON) "bin/zx02pack.py" "$(BEEBLINK_VOLUME)/1/$$.SCREEN$(INDEX)" "$(BEEB_BUILD)/Z.SCREEN$(INDEX)" $(newline))

##########################################################################
##########################################################################

.PHONY:_adfs_image
_adfs_image: BOOT=$(error must specify BOOT)
_adfs_image: DISK_CONTENTS=$(error must specify DISK_CONTENTS)
_adfs_image: PC_IMAGE=$(error must specify PC_IMAGE)
_adfs_image: BBC_IMAGE=$(error must specify BBC_IMAGE)
_adfs_image: TITLE=
_adfs_image:
	$(_V)$(SHELLCMD) mkdir "$(DISK_CONTENTS)"

# Form ADFS disk contents in $(DISK_CONTENTS): !BOOT and its .inf.
#	$(_V)$(SHELLCMD) concat -o "$(DISK_CONTENTS)/!BOOT" --pad 653568 "$(BOOT)"
	$(_V)$(SHELLCMD) copy-file "$(BOOT)" "$(DISK_CONTENTS)/!BOOT"
	$(_V)echo "$$.!BOOT FFFFFFFF FFFFFFFF" > "$(DISK_CONTENTS)/!BOOT.inf"

# Create the ADFS disk image.
	$(_V)$(PYTHON) "$(BEEB_BIN)/adf_create.py" -o "$(BUILD)/$(PC_IMAGE)" --opt4 3 --title "$(TITLE)" "$(DISK_CONTENTS)/!BOOT"

# Copy the ADFS disk image somewhere the BBC can see it too.
	$(_V)$(SHELLCMD) copy-file "$(BUILD)/$(PC_IMAGE)" "$(BEEB_BUILD)/L.$(BBC_IMAGE)"

# Create *EXEC file for quickly writing the disk image.
	$(_V)$(SHELLCMD) echo-bytes -o "$(BEEB_BUILD)/!.$(BBC_IMAGE)" -e _ "CHAIN_22::BEEBLINK:0._24.IMAGER_22_0dWA0AA:Z.L.$(BBC_IMAGE)_0d"

##########################################################################
##########################################################################

.PHONY: clean
clean:
	$(_V)$(SHELLCMD) rm-tree "$(BUILD)"
	$(_V)$(SHELLCMD) rm-tree "$(BEEB_BUILD)"
	$(_V)$(SHELLCMD) rm-tree "$(BEEBLINK_VOLUME)/$(TEST_DISK_BEEBLINK_DRIVE)"
ifneq ($(UNAME),Windows_NT)
	$(_V)cd "$(ZX02_PATH)" && $(GNU_MAKE) clean
# doesn't seem to do a proper clean?
	$(_V)$(SHELLCMD) rm-tree "$(ZX02_PATH)/build"
endif

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
_tom_emacs: _DISK:=$(BUILD)/test_disk.adl
_tom_emacs:
	$(_V)$(MAKE) build
#	curl --connect-timeout 0.25 --silent -G 'http://localhost:48075/reset/b2' --data-urlencode "config=$(_CONFIG)"
	curl --connect-timeout 0.25 --silent -H 'Content-Type:application/binary' --upload-file '$(_DISK)' 'http://localhost:48075/mount/b2?drive=0&name=$(_DISK)'
