import boot_builder,os.path

# List of files that go into the build is defined here.
#
# Files will be arranged on disk in the specific order given.
#
# This gets called more than once during the build and the results
# must be the same each time.
def make_files_list():
    drive1='''beeb/fdload_adfsl/1/'''
    files=[]

    for i in range(222):
        files.append(boot_builder.File(path=os.path.join(drive1,'''$.SCREEN%d'''%i),
                                       ident='screen%d'%i,
                                       compressed=True))

    return files
