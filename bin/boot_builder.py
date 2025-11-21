#!/usr/bin/python3
import sys,os,argparse,collections,json,dataclasses,importlib,importlib.util,struct,hashlib,subprocess

##########################################################################
##########################################################################

def fatal(msg):
    sys.stderr.write('FATAL: %s\n'%msg)
    sys.exit(1)

##########################################################################
##########################################################################

def makedirs(path):
    if not os.path.isdir(path): os.makedirs(path)

def load_file(path):
    with open(path,'rb') as f: return f.read()

def save_file(path,data):
    with open(path,'wb') as f: f.write(data)

##########################################################################
##########################################################################

# path = path of file on disk, relative to root of working copy.
#
# ident = suffix for the identifier used to refer to this file in
# the 6502 code.

ZX02CacheEntry=collections.namedtuple('ZX02CacheEntry',
                                      'u_data u_hash u_path c_folder c_path')

# TODO: could/should this be a dataclass?
class File:
    def __init__(self,path,ident,compressed=False):
        self._path=path
        self._ident=ident
        self._compressed=compressed
        self._options=None
        self._disk_data=None    # may be compressed
        self._memory_data=None

    @property
    def path(self): return self._path

    @property
    def ident(self): return self._ident

    @property
    def compressed(self): return self._compressed

    def set_options(self,options):
        assert self._options is None
        self._options=options

    def get_memory_data(self):
        if self._memory_data is None:
            self._memory_data=load_file(self._path)
        assert self._memory_data is not None
        return self._memory_data

    def _get_zx02_cache_entry(self):
        assert self.compressed
        u_data=self.get_memory_data()
        u_hash=hashlib.sha256(u_data).hexdigest()
        c_folder=os.path.join(self._options.g_zx02_cache_path,u_hash[:3])
        c_path=os.path.join(c_folder,'%s.zx02'%u_hash)
        return ZX02CacheEntry(u_data=u_data,
                              u_hash=u_hash,
                              u_path=self.path,
                              c_folder=c_folder,
                              c_path=c_path)

    def get_disk_data(self):
        if self._disk_data is None:
            if self.compressed:
                ent=self._get_zx02_cache_entry()
                if not os.path.isfile(ent.c_path):
                    makedirs(ent.c_folder)
                    argv=[self._options.g_zx02_path,
                          ent.u_path,
                          ent.c_path]
                    subprocess.run(argv,check=True)
                self._disk_data=load_file(ent.c_path)
            else: self._disk_data=self.get_memory_data()
        assert self._disk_data is not None
        return self._disk_data
    
def warm_zx02_cache_cmd(files,options):
    ent_by_hash={}
    for file in files:
        if file.compressed and os.path.isfile(file.path):
            ent=file._get_zx02_cache_entry()
            if not os.path.isfile(ent.c_path): ent_by_hash[ent.u_hash]=ent

    if len(ent_by_hash)==0: return # no warming required.
    
    makefile_path=os.path.join(options.g_intermediate_folder_path,
                               'zx02_cache_warmup_makefile.mak')
    def target(ent): return 'f_%s'%ent.u_hash

    all_targets=' '.join([target(ent) for ent in ent_by_hash.values()])
    with open(makefile_path,'wt') as f:
        f.write('.PHONY:all %s\n'%all_targets)
        f.write('all: %s\n'%all_targets)
        number=1
        for hash,ent in ent_by_hash.items():
            f.write('%s:\n'%target(ent))
            f.write('\t@echo Compressing file: %d/%d\n'%(number,len(ent_by_hash)))

            # qnd $ quoting for GNU Make purposes.
            quoted_u_path=ent.u_path.replace('$','$$')
            f.write('\t@"%s" "%s" "%s" > "%s"\n'%(options.g_zx02_path,
                                               quoted_u_path,
                                               ent.c_path,
                                               '%s.txt'%ent.c_path))
            makedirs(ent.c_folder)
            number+=1

    argv=[options.make_path,
          '-j',str(os.cpu_count()),
          '-f',makefile_path]
    subprocess.run(argv,check=True)
    
##########################################################################
##########################################################################

# def get_compressed_path(file,):
#     assert file.compressed

#     return os.path.join(options.g_intermediate_folder_path,
#                         '%s.zx02'%file.ident)

# def get_disk_path(file,options):
#     if file.compressed: return get_compressed_path(file,options)
#     else: return file.path

##########################################################################
##########################################################################

# https://stackoverflow.com/a/51286749/1618406
# class JSONEncoder2(json.JSONEncoder):
#     def default(self,o):
#         if dataclasses.is_dataclass(o): return dataclasses.asdict(o)
#         return super().default(o)

##########################################################################
##########################################################################

PRG=collections.namedtuple('PRG','addr data')

def load_prg(path):
    data=load_file(path)

    if len(data)<3: fatal('file too small to be a C64 .PRG: %s'%path)

    return PRG(addr=data[0]|data[1]<<8,data=bytearray(data[2:]))

##########################################################################
##########################################################################

def get_smaller_str(x):
    xs='&%X'%x
    
    dword=int(x&(1<<31)-1)
    if x&(1<<31): dword+=-(1<<31)
    ds='%d'%dword

    return ds if len(ds)<len(xs) else xs

def get_exec_part(options):
    loader0=load_prg(options.loader0_path)

    while len(loader0.data)%4!=0: loader0.data.append(0)

    lines=[]
    for i in range(0,len(loader0.data),4):
        addr=loader0.addr+i
        dword=(loader0.data[i+0]|
               loader0.data[i+1]<<8|
               loader0.data[i+2]<<16|
               loader0.data[i+3]<<24)
        stmt='!%s=%s'%(get_smaller_str(addr),get_smaller_str(dword))

        # BASIC 4 input buffer size is $ee (see
        # https://8bs.com/basic/basic4-b8b6.htm) - leave a bit of
        # slack
        if len(lines)>0 and len(lines[-1])+1+len(stmt)<0xe0:
            assert len(lines[-1])>0
            lines[-1]+=':'+stmt
        else: lines.append(stmt)

    lines.append('CALL%s'%get_smaller_str(loader0.addr))

    result=bytearray()
    result+=b'*BASIC\r'
    if options.vdu21:
        result+=b'V.12,23,1;0;0;0;0,21\r'
        result+=b'V.6:P."LOADING...";:V.21\r'
    for line_index,line in enumerate(lines):
        result+=line.encode('ascii')
        # no harm in having the VDU6 always there
        if line_index==len(lines)-1: result.append(6)
        result.append(13)

    return result

# def get_filler(n): return n*b'\x00'

def check_budget(data,max_size,description):
    
    if len(data)>max_size:
        fatal('too large: %d bytes (max is %d; overrun by %d): %s'%
              (len(data),max_size,len(data)-max_size,description))

# def check_budget_and_pad(data,max_size,description):
#     assert isinstance(data,bytearray),type(data)

#     check_budget(data,max_size,description)

#     data+=bytearray(max_size-len(data))

##########################################################################
##########################################################################

# @dataclasses.dataclass
# class TOCEntry:
#     ident:str
#     path:str
#     index:int
#     ltrack:int
#     sector:int
#     num_bytes:int

TOCEntry=collections.namedtuple('TOCEntry','file index ltrack sector num_bytes')

##########################################################################
##########################################################################

def get_fdload_data_path(options):
    return os.path.join(options.g_intermediate_folder_path,
                        'fdload.dat')

MAX_FDLOAD_DATA_SIZE=2*79*16*256

def build_fdload_data_cmd(files,options):
    fdload_data=bytearray()
    
    toc=[]
    file_contents=[]

    # assert len(fdload_data)==4096
    for file_index,file in enumerate(files):
        file_data=file.get_disk_data()

        if len(file_data)==0: fatal('unsupported 0 byte file: %s'%file.path)

        check_budget(file_data,65536,file.path)

        assert len(fdload_data)%256==0
        lsector=32+len(fdload_data)//256
        
        toc.append(TOCEntry(file=file,
                            index=file_index,
                            ltrack=lsector//16,
                            sector=lsector%16,
                            num_bytes=len(file_data)))
        #file_contents.append(file_data)

        fdload_data+=file_data
        n=len(fdload_data)%256
        if n!=0: fdload_data+=bytearray(256-n)

    check_budget(fdload_data,MAX_FDLOAD_DATA_SIZE,'fdload data')

    # # assert len(toc)==len(file_contents)
    # # for i in range(len(toc)): assert toc[i].num_bytes==len(file_contents[i])

    # # max_fdload_data_size=(2*80-1)*16*256
    # # check_budget_and_pad(fdload_data,max_fdload_data_size,'output big file')

    # # The output big file is in fdload logical sector order. Rearrange
    # # so that it is in the ADFS sector order expected by adf_create.
    # output_data=bytearray()
    # for side in range(2):
    #     for track in range(80):
    #         if track==0 and side==0:
    #             # there is no fdload data in this area.
    #             continue

    #         ltrack=track*2+side-1
    #         assert ltrack>=0 and ltrack<159
            
    #         i=ltrack*4096
    #         j=len(output_data)
    #         if i>len(fdload_data): output_data+=bytearray(4096)
    #         else: output_data+=fdload_data[i:i+4096]

    #         # if track>=1:
    #         #     output_data[j+0]=side
    #         #     output_data[j+1]=track

    # # Prepend the 9 sectors of loader0.
    # output_data=exec_data+output_data
    # assert len(output_data)==(2*80*16-7)*256

    def open_output_file(name,mode):
        path=os.path.join(options.g_intermediate_folder_path,name)
        return open(path,mode)

    save_file(get_fdload_data_path(options),fdload_data)

    toc_json={
        'num_files':len(toc),
        'files':[],
    }
    for index,entry in enumerate(toc):
        toc_json['files'].append({
            'ident':entry.file.ident,
            'path':entry.file.path,
            'compressed':entry.file.compressed,
            'index':index,
            'ltrack':entry.ltrack,
            'sector':entry.sector,
            'num_bytes':entry.num_bytes,
        })
        
    with open_output_file('toc.json','wt') as f:
        json.dump(toc_json,f,indent=4*' ')

    toc_binary=bytearray()
    toc_binary.append(len(toc))
    for entry in toc:
        assert entry.ltrack>=0 and entry.ltrack<160
        toc_binary.append(entry.ltrack)

        flags_and_sector=0
        assert entry.sector>=0 and entry.sector<16
        flags_and_sector|=entry.sector
        if entry.file.compressed: flags_and_sector|=0x80
        toc_binary.append(flags_and_sector)

        toc_binary.append(-entry.num_bytes&0xff)
        toc_binary.append(-entry.num_bytes>>8&0xff)

    with open_output_file('toc.dat','wb') as f: f.write(toc_binary)

    # if options.output_beeblink_path is not None:
    #     makedirs(options.output_beeblink_path)
    #     for i in range(len(file_contents)):
    #         with open(os.path.join(options.output_beeblink_path,
    #                                  '''$.%d'''%i),'wb') as f:
    #             f.write(file_contents[i])

    #     count=bytearray()
    #     count.append(len(file_contents))
    #     with open(os.path.join(options.output_beeblink_path,'''$.COUNT'''),
    #               'wb') as f:
    #         f.write(count)

##########################################################################
##########################################################################
    
def build_disk_contents_cmd(files,options):
    exec_data=get_exec_part(options)

    # Provided the *EXEC part is smaller than this, it will fit into
    # track 0, simplifying the pretence that ADFS and fdload have
    # compatible views of the disk.
    #
    # (The ADFS metadata is 7 sectors, so there's 9 sectors left in
    # track 0.)
    exec_data_size=9*256
    check_budget(exec_data,exec_data_size,'loader8 in *EXEC form')

    # Load fdload data.
    fdload_data=load_file(get_fdload_data_path(options))
    check_budget(fdload_data,MAX_FDLOAD_DATA_SIZE,'fdload data')
    
    # Load loader1.
    loader1_size=4096
    loader1=load_prg(options.loader1_path)
    check_budget(loader1.data,loader1_size,'loader1 data')

    # Arrange the data in ADFS sector order.
    output_data=bytearray()
    for side in range(2):
        for track in range(80):
            if track==0 and side==0:
                output_data+=exec_data
                output_data+=bytearray(exec_data_size-len(output_data))
            elif track==0 and side==1:
                # this is where loader1 goes.
                output_data+=loader1.data
                output_data+=bytearray(loader1_size-len(loader1.data))
            else:
                ltrack=(track-1)*2+side
                assert ltrack>=0 and ltrack<159
            
                i=ltrack*4096
                j=len(output_data)
                if i>len(fdload_data): output_data+=bytearray(4096)
                else:
                    part=fdload_data[i:i+4096]
                    output_data+=part
                    output_data+=bytearray(4096-len(part))

    expected_output_data_size=(2*80*16-7)*256
    assert len(output_data)==expected_output_data_size,(expected_output_data_size,len(output_data))

    makedirs(options.output_folder_path)
    save_file(os.path.join(options.output_folder_path,'!BOOT'),output_data)

    with open(os.path.join(options.output_folder_path,'!BOOT.inf'),
              'wt') as f:
        f.write('$.!BOOT FFFFFFFF FFFFFFFF\n')
    
##########################################################################
##########################################################################

def prepare_cmd(files,options):
    makedirs(options.g_intermediate_folder_path)
    with open(options.output_asm_path,'wt') as f:
        for file_index,file in enumerate(files):
            f.write('file_%s=%d ; %s\n'%(file.ident,file_index,file.path))

##########################################################################
##########################################################################

def beeblink_cmd(files,options):
    makedirs(options.output_folder_path)
    for file_index,file in enumerate(files):
        save_file(os.path.join(options.output_folder_path,'$.%d'%file_index),
                  file.get_disk_data())

    save_file(os.path.join(options.output_folder_path,'$.COUNT'),
              struct.pack('<I',len(files)))

##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()
    parser.add_argument('-l','--list',metavar='FILE',dest='g_list_py_path',required=True,help='''use Python script %(metavar)s to get files list''')
    parser.add_argument('--intermediate-folder',metavar='PATH',dest='g_intermediate_folder_path',required=True,help='''put intermediate file(s) somewhere in %(metavar)s''')
    # I am too lazy to do the environment variable thing here. It
    # doesn't matter as it's easy to deal with from the Makefile.
    parser.add_argument('--zx02',metavar='PATH',dest='g_zx02_path',required=True,help='''treat %(metavar)s as path to zx02 binary''')
    parser.add_argument('--zx02-cache',metavar='PATH',dest='g_zx02_cache_path',required=True,help='''use %(metavar)s as zx02 cache path''')

    subparsers=parser.add_subparsers()

    def add_subparser(name,fun,**kwargs):
        subparser=subparsers.add_parser(name,**kwargs)
        subparser.set_defaults(fun=fun)
        return subparser

    prepare_subparser=add_subparser('prepare',prepare_cmd,help='''find and compress files and generate a constants file with file indexes''')
    prepare_subparser.add_argument('--output-asm',metavar='FILE',dest='output_asm_path',help='''write output to %(metavar)s rather than stdout''')

    warm_zx02_cache_subparser=add_subparser('warm-zx02-cache',warm_zx02_cache_cmd,help='''warm up zx02 cache as much as possible''')
    warm_zx02_cache_subparser.add_argument('--make',metavar='PATH',dest='make_path',default='make',help='''use %(metavar)s as path to GNU Make. Default: %(default)s''')

    build_fdload_data_subparser=add_subparser('build-fdload-data',build_fdload_data_cmd,help='''generate fdload-friendly part of big data''')

    build_disk_contents_subparser=add_subparser('build-disk-contents',build_disk_contents_cmd,help='''generate disk contents''')
    
    build_disk_contents_subparser.add_argument('--loader0',metavar='FILE',required=True,dest='loader0_path',help='''read loader0 code from %(metavar)s, a C64 .prg''')
    build_disk_contents_subparser.add_argument('--loader1',metavar='FILE',required=True,dest='loader1_path',help='''read loader1 code from %(metavar)s, a C64 .prg''')
    build_disk_contents_subparser.add_argument('--vdu21',action='store_true',help='''add a VDU21 in the *EXECable part''')
    build_disk_contents_subparser.add_argument('output_folder_path',metavar='FOLDER',help='''write disk contents to %(metavar)s''')

    beeblink_subparser=add_subparser('beeblink',beeblink_cmd,help='''generate BeebLink DFS-type drive with contents of disk''')
    beeblink_subparser.add_argument('output_folder_path',metavar='FOLDER',help='''write files to %(metavar)s''')
    
    options=parser.parse_args(argv)
    if options.fun is None:
        parser.print_help()
        sys.exit(1)

    # https://stackoverflow.com/a/54956419/1618406
    spec=importlib.util.spec_from_file_location('file_list',
                                                options.g_list_py_path)
    file_list_module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(file_list_module)

    files=file_list_module.make_files_list()
    idents_seen=set()
    for file in files:
        if file.ident in idents_seen:
            fatal('duplicate ident in files list: %s'%file.ident)
        idents_seen.add(file.ident)
        file.set_options(options)

    options.fun(files,options)
    
##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
