import boot_builder,os.path

# List of files that go into the build is defined here.
#
# Files will be arranged on disk in the specific order given.
#
# This gets called more than once during the build and the results
# must be the same each time.
def make_files_list():
    files=[]

    files.append(boot_builder.File(path='build/demo_scroller0.bin',
                                   ident='scroller0_bin'))

    return files
