import boot_builder,os.path

# List of files that go into the build is defined here.
#
# Files will be arranged on disk in the specific order given.
def make_files_list():
    drive1='''beeb/adfsl_fixed_layout/1/'''
    files=[]

    # # 1 byte. Occupies L2 S0.
    # files.append(boot_builder.File(path='data/n1.dat',ident='n1'))

    # # 3841 bytes. Occupies L2 S1-L3 S0 inclusive.
    # files.append(boot_builder.File(path='data/n3841.dat',ident='n3841'))

    for i in range(10):
        files.append(boot_builder.File(path=os.path.join(drive1,'''$.SCREEN%d'''%i),
                                       ident='screen%d'%i))

    for i in range(2):
        files.append(boot_builder.File(path=os.path.join(drive1,'''$.PSCREEN%d'''%i),
                                    ident='pscreen%d'%i))

    return files

