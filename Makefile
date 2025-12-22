MAKEFLAGS+=--no-print-directory

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
# The GNU Make supplied with Xcode is old!
RECENT_GNU_MAKE:=gmake --no-print-directory
else
RECENT_GNU_MAKE:=$(MAKE)
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
BEEBLINK_VOLUME:=$(PWD)/beeb/fdload_adfsl

# Where BBC build output goes.
BEEB_BUILD:=$(BEEBLINK_VOLUME)/Z

# ZX02 stuff.
ZX02_PATH:=$(PWD)/submodules/zx02
ifeq ($(UNAME),Windows_NT)
ZX02:=$(PWD)/bin/zx02.exe
else
ZX02:=$(ZX02_PATH)/build/zx02
endif

BUILDER_ZX02_ARGS:=--zx02 "$(ZX02)" --zx02-cache "$(BUILD)/zx02_cache"

##########################################################################
##########################################################################

TEST_DISK_LIST_PY:=bin/test_disk_files.py
TEST_DISK_INTERMEDIATES:=$(BUILD)/test_disk/intermediates
TEST_DISK_CONTENTS:=$(BUILD)/test_disk/contents
TEST_DISK_BUILDER_ARGS:=--list "$(TEST_DISK_LIST_PY)" --intermediate-folder "$(TEST_DISK_INTERMEDIATES)" $(BUILDER_ZX02_ARGS)
TEST_DISK_BEEBLINK_PATH:=$(BEEBLINK_VOLUME)/Y

##########################################################################
##########################################################################

PICS_DISK_LIST_PY:=bin/pics_disk_files.py
PICS_DISK_INTERMEDIATES:=$(BUILD)/pics_disk/intermediates
PICS_DISK_CONTENTS:=$(BUILD)/pics_disk/contents
PICS_DISK_BUILDER_ARGS:=--list "$(PICS_DISK_LIST_PY)" --intermediate-folder "$(PICS_DISK_INTERMEDIATES)" $(BUILDER_ZX02_ARGS)

##########################################################################
##########################################################################

DEMO_DISK_LIST_PY:=bin/demo_disk_files.py
DEMO_DISK_INTERMEDIATES:=$(BUILD)/demo_disk/intermediates
DEMO_DISK_CONTENTS:=$(BUILD)/demo_disk/contents
DEMO_DISK_BUILDER_ARGS:=--list "$(DEMO_DISK_LIST_PY)" --intermediate-folder "$(DEMO_DISK_INTERMEDIATES)" $(BUILDER_ZX02_ARGS)

##########################################################################
##########################################################################

.PHONY: build
build: _output_folders $(BUILD)/GhoulsRevenge.bbc.dat $(BUILD)/TitleScreen_BBC.bbc.dat
# Build prerequisites.
ifneq ($(UNAME),Windows_NT)
	$(_V)test -f "$(ZX02)" || (cd "$(ZX02_PATH)" && $(RECENT_GNU_MAKE) all)
endif

# Create the files list.
	$(_V)$(PYTHON) "bin/boot_builder.py" $(TEST_DISK_BUILDER_ARGS) prepare --output-asm "$(BUILD)/test_disk_files.generated.s65"
	$(_V)$(PYTHON) "bin/boot_builder.py" $(PICS_DISK_BUILDER_ARGS) prepare --output-asm "$(BUILD)/pics_disk_files.generated.s65"
	$(_V)$(PYTHON) "bin/boot_builder.py" $(DEMO_DISK_BUILDER_ARGS) prepare --output-asm "$(BUILD)/demo_disk_files.generated.s65"

# Build any part files.
	$(_V)$(PYTHON3) "bin/make_bbc_font.py" -o "$(BUILD)/bbc_font.generated.s65" "data/utils.3.50.rom"
	$(_V)$(MAKE) _asm PC=demo_scroller0 EXTRACT_PRG=1

# Warm up the ZX02 cache in parallel. 
	$(_V)$(PYTHON) "bin/boot_builder.py" $(TEST_DISK_BUILDER_ARGS) warm-zx02-cache --make "$(MAKE)"
	$(_V)$(PYTHON) "bin/boot_builder.py" $(PICS_DISK_BUILDER_ARGS) warm-zx02-cache --make "$(MAKE)"
	$(_V)$(PYTHON) "bin/boot_builder.py" $(DEMO_DISK_BUILDER_ARGS) warm-zx02-cache --make "$(MAKE)"

# Build the big file.
	$(_V)$(PYTHON) "bin/boot_builder.py" $(TEST_DISK_BUILDER_ARGS) build-fdload-data
	$(_V)$(PYTHON) "bin/boot_builder.py" $(PICS_DISK_BUILDER_ARGS) build-fdload-data
	$(_V)$(PYTHON) "bin/boot_builder.py" $(DEMO_DISK_BUILDER_ARGS) build-fdload-data

# Assemble stuff
	$(_V)$(MAKE) _asm PC=loader0 BEEB=LOADER0
	$(_V)$(MAKE) _asm PC=loader1 BEEB=LOADER1
	$(_V)$(MAKE) _asm PC=pics_loader1
	$(_V)$(MAKE) _asm PC=demo_loader1

# Put together disk contents
	$(_V)$(PYTHON) "bin/boot_builder.py" $(TEST_DISK_BUILDER_ARGS) build-disk-contents --vdu21 --loader0 "$(BUILD)/loader0.prg" --loader1 "$(BUILD)/loader1.prg" "$(TEST_DISK_CONTENTS)"
	$(_V)$(PYTHON) "bin/boot_builder.py" $(PICS_DISK_BUILDER_ARGS) build-disk-contents --vdu21 --loader0 "$(BUILD)/loader0.prg" --loader1 "$(BUILD)/pics_loader1.prg" $(PICS_DISK_CONTENTS)
	$(_V)$(PYTHON) "bin/boot_builder.py" $(DEMO_DISK_BUILDER_ARGS) build-disk-contents --vdu21 --loader0 "$(BUILD)/loader0.prg" --loader1 "$(BUILD)/demo_loader1.prg" $(DEMO_DISK_CONTENTS)

# Create BeebLink folders.
	$(_V)$(PYTHON) "bin/boot_builder.py" $(TEST_DISK_BUILDER_ARGS) beeblink "$(TEST_DISK_BEEBLINK_PATH)"

# Assemble a version of the fdload code that's vaguely testable from
# BASIC.
	$(_V)$(MAKE) _asm PC=fdload_test BEEB=FDLOAD

	$(_V)$(MAKE) _adfs_image "BOOT=$(TEST_DISK_INTERMEDIATES)/boot.dat" "DISK_CONTENTS=$(TEST_DISK_CONTENTS)" "PC_IMAGE=test_disk.adl" "BBC_IMAGE=TEST"
	$(_V)$(MAKE) _adfs_image "BOOT=$(PICS_DISK_INTERMEDIATES)/boot.dat" "DISK_CONTENTS=$(PICS_DISK_CONTENTS)" "PC_IMAGE=pics_disk.adl" "BBC_IMAGE=PICS"
	$(_V)$(MAKE) _adfs_image "BOOT=$(DEMO_DISK_INTERMEDIATES)/boot.dat" "DISK_CONTENTS=$(DEMO_DISK_CONTENTS)" "PC_IMAGE=demo_disk.adl" "BBC_IMAGE=DEMO"

##########################################################################
##########################################################################

$(BUILD)/GhoulsRevenge.bbc.dat : data/GhoulsRevenge.png
	$(_V)$(PYTHON) "$(BEEB_BIN)/png2bbc.py" -o "$@" "$<" 2

$(BUILD)/TitleScreen_BBC.bbc.dat : data/TitleScreen_BBC.png
	$(_V)$(PYTHON) "$(BEEB_BIN)/png2bbc.py" -o "$@" "$<" 2 --160

##########################################################################
##########################################################################

.PHONY:_adfs_image
_adfs_image: DISK_CONTENTS=$(error must specify DISK_CONTENTS)
_adfs_image: PC_IMAGE=$(error must specify PC_IMAGE)
_adfs_image: BBC_IMAGE=$(error must specify BBC_IMAGE)
_adfs_image: TITLE=
_adfs_image:
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
	$(_V)$(SHELLCMD) rm-tree "$(TEST_DISK_BEEBLINK_PATH)"
ifneq ($(UNAME),Windows_NT)
	$(_V)cd "$(ZX02_PATH)" && $(RECENT_GNU_MAKE) clean
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
	$(if $(EXTRACT_PRG),$(_V)$(PYTHON) "$(BEEB_BIN)/prg2bbc.py" $(PRG2BBC_EXTRA_ARGS) --io "$(BUILD)/$(PC).prg" "$(BUILD)/$(PC).bin")
	$(if $(BEEB),$(_V)$(PYTHON) "$(BEEB_BIN)/prg2bbc.py" $(PRG2BBC_EXTRA_ARGS) --io "$(BUILD)/$(PC).prg" "$(BEEB_BUILD)/$$.$(BEEB)")

##########################################################################
##########################################################################

.PHONY: _tom_emacs
_tom_emacs: _CONFIG:=MOS 3.50r + BeebLink
_tom_emacs: _CONFIG:=Master 128 (MOS 3.50)
_tom_emacs: _DISK:=$(BUILD)/test_disk.adl
_tom_emacs: _DISK:=$(BUILD)/pics_disk.adl
_tom_emacs: _DISK:=$(BUILD)/demo_disk.adl
_tom_emacs:
	$(_V)$(MAKE) build
	curl --fail-with-body --connect-timeout 0.25 --silent 'http://localhost:48075/reset/b2' --data-urlencode "config=$(_CONFIG)"
	curl --fail-with-body --connect-timeout 0.25 --silent -H 'Content-Type:application/binary' --upload-file '$(_DISK)' 'http://localhost:48075/mount/b2?drive=0&name=$(_DISK)'
# (the pasting interferes with the FS boot key, so it ends up in ROM
# or tape filing system or whatever. But: it doesn't matter, because
# it selects *ADFS manually.)
	$(_V)$(SHELLCMD) echo-bytes -o "$(BUILD)/paste.dat" -e _ "*ADFS_0d*EXEC !BOOT_0d"
	curl --fail-with-body --connect-timeout 0.25 --silent -H 'Content-Type:text/plain;charset:utf-8' --upload-file "$(BUILD)/paste.dat" "http://localhost:48075/paste/b2"

##########################################################################
##########################################################################

# Phony target for manual invocation. It doesn't run on every build,
# because it needs the VC++ command line tools on the path, something
# I don't want to require.

.PHONY:zx02_windows
zx02_windows: SRC:=$(PWD)/submodules/zx02/src
zx02_windows: _output_folders
	cd "$(BUILD)" && cl /W4 /Zi /O2 /Fe$(PWD)/bin/zx02.exe "$(SRC)/compress.c" "$(SRC)/memory.c" "$(SRC)/optimize.c" "$(SRC)/zx02.c"
