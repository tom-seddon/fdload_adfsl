#!/usr/bin/python3
import sys,os,os.path,argparse,subprocess,hashlib

##########################################################################
##########################################################################

def fatal(msg):
    sys.stderr.write('FATAL: %s\n'%msg)
    sys.exit(1)

##########################################################################
##########################################################################

def load_file(path):
    with open(path,'rb') as f: return f.read()

def save_file(path,data):
    with open(path,'wb') as f: f.write(data)

def main2(options):
    if options.zx02_path is None: fatal('no zx02 path provided')
    if options.cache_path is None: fatal('no cache path provided')

    uncompressed_data=load_file(options.input_path)

    hash=hashlib.sha256(uncompressed_data).hexdigest()

    cache_folder=os.path.join(options.cache_path,hash[:3])
    cache_compressed_path=os.path.join(cache_folder,'%s.zx02'%hash)

    if not os.path.isfile(cache_compressed_path):
        if not os.path.isdir(cache_folder): os.makedirs(cache_folder)

        cache_uncompressed_path=os.path.join(cache_folder,'%s.dat'%hash)

        save_file(cache_uncompressed_path,uncompressed_data)

        argv=[options.zx02_path,
              cache_uncompressed_path,
              cache_compressed_path]
        subprocess.run(argv,check=True)

    compressed_data=load_file(cache_compressed_path)
    save_file(options.output_path,compressed_data)

##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()

    zx02_path_env_var='ZX02PACK_ZX02'
    cache_path_env_var='ZX02PACK_CACHE'

    def get_env_var_help_suffix(name):
        suffix='''. Use environment variable %s to provide default for use when not specified'''%name

        value=os.getenv(name)
        if value is not None: suffix+='''. Default: %s'''%value

        return suffix
    
    parser.add_argument('--zx02',metavar='FILE',dest='zx02_path',default=os.getenv(zx02_path_env_var),help='''treat %(metavar)s as path to zx02'''+get_env_var_help_suffix(zx02_path_env_var))
    parser.add_argument('--cache',metavar='PATH',dest='cache_path',default=os.getenv(cache_path_env_var),help='''use %(metavar)s as cache'''+get_env_var_help_suffix(cache_path_env_var))
    parser.add_argument('input_path',metavar='INPUT-FILE',help='''read uncompressed data from %(metavar)s''')
    parser.add_argument('output_path',metavar='OUTPUT-FILE',help='''write compressed data to %(metavar)s''')

    main2(parser.parse_args(argv))

##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
