BBC Master 128/Compact double density floppy disk loading code.
Bypasses the OS, so all of memory can be used. Data to be loaded is
packed into a file on an ordinary ADFS L disk (~630 KB effective
capacity), bootable using SHIFT+BREAK and copyable using
`*COPY`/`*BACKUP`.

# Build

## Prerequisites

### Windows

- Git on PATH
- Python 3.x

### Linux

- Git
- C compiler
- Python 3.x
- GNU Make

### macOS

- Git
- C compiler (Xcode will do)
- Python 3.x (macOS Ventura+ system Python is good enough)
- GNU Make 4 (install from MacPorts/homebrew - the Xcode version is
  too old)

## Clone the repo

This repo has submodules. Clone it with `--recursive`:

    git clone --recursive https://github.com/tom-seddon/fdload_adfsl
		
Alternatively, if you already cloned it non-recursively, you can do
the following from inside the working copy:

    git submodule init
	git submodule update

(The source zip files that GitHub makes available are no good. The
only supported way to build this project is to clone it from GitHub as
above.)

## Build

Run `make` in the working copy. (A `make.bat` is supplied for Windows,
which will run the supplied copy of GNU Make.)

Build output can be found in the `build` folder:

- `pics_disk.adl` - 4-odd MBytes of Mode 1 images compressed onto one
  ADFS L disk
- `demo_disk.adl` - WIP BBC Master demo effects

# Licence

Licence: https://www.gnu.org/licenses/gpl-3.0.en.html
