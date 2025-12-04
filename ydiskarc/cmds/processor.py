import logging

import yaml
import requests
import os.path
import json
import re
from os.path import expanduser
# import shutil
from rich.progress import Progress, TextColumn

from urllib.parse import unquote
import hashlib


# TODO: дату изменения менять на правильную?
# TODO: многопоточность и шоп целиком завершалось по первому требованию! и шоп не висло после сна!
# TODO: шоп не вываливалось целиком ежели не получилось скачать один файл! а записывало это в лог



YD_API = 'https://cloud-api.yandex.net/v1/disk/public/resources'
YD_API_DOWNLOAD = 'https://cloud-api.yandex.net/v1/disk/public/resources/download'

# REQUEST_HEADER = {'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Mobile Safari/537.36'} # with these headers some file with exotic characters in the name are not downloaded!
REQUEST_HEADER = None

# DEFAULT_CHUNK_SIZE = 32765
DEFAULT_CHUNK_SIZE = 1024768

def url_to_dir_list(path):
    return [i.rstrip().replace("\"","-") for i in path.split('/')] # somehow in yandex disk there may be quotes in file names!!!1


def get_file(url, filepath=None, filename=None, params=None, aria2=False, aria2path=None, makedirs=True, filesize=None):
    progress = Progress(TextColumn("[progress.description]{task.description}"),)
    if filesize is not None:
        task1 = progress.add_task("[green]Downloading...", total=int(filesize))
    msg = 'Retrieving file from %s' % (url) if filesize is None else 'Retrieving file from %s with size %d' % (url, filesize)
    logging.info(msg)
    if params:
        # print(f"page = requests.get(\"{url}\", {params}, headers={REQUEST_HEADER}, stream=True, verify=True)")
        page = requests.get(url, params, headers=REQUEST_HEADER, stream=True, verify=True)
    else:
        # print(f"page = requests.get(\"{url}\", headers={REQUEST_HEADER}, stream=True, verify=True)")
        page = requests.get(url, headers=REQUEST_HEADER, stream=True, verify=True)
    
    if filename is None:
        if "Content-Disposition" in page.headers.keys():
            fname = re.findall("filename=(.+)", page.headers["Content-Disposition"])[0].strip('"').encode('latin-1').decode('utf-8')
        else:
            fname = url.split("/")[-1]
        if filepath:
            filename = os.path.join(filepath, fname)
        else:
            filename = fname
    elif filepath is not None:
            filename = os.path.join(filepath, filename)
    filename = filename.replace("\"","-")
    
    if page.status_code != requests.status_codes.codes.ALL_OK:
        logging.warning(f"Error {page.status_code} getting {filename} : {page.text} : {page.reason}")
        return
    
    if not aria2:
        # filename_tmp = filename + ".ydiskarc_download"
        filename_tmp = filename + ".download"
        f = open(filename_tmp, 'wb')
        total = 0
        chunk = 0
        for line in page.iter_content(chunk_size=DEFAULT_CHUNK_SIZE):
            chunk += 1
            if line:
                f.write(line)
            total += len(line)
            if filesize is not None:
#               logging.debug('File %s to size %d' % (filename, total))               
                progress.update(task1, advance=len(line))
            if chunk % 1000 == 0:
                logging.debug('File %s to size %d' % (filename, total))
                # print(".", end = "")
                pass
        f.close()
        os.replace(filename_tmp, filename)
        logging.info('Saved %s' % filename)
    else:
        dirpath = os.path.dirname(filename)
        basename = os.path.basename(filename)
        if len(dirpath) > 0:
            s = "%s --retry-wait=10 -d %s --out=%s %s" % (aria2path, dirpath, basename, url)
        else:
            s = "%s --retry-wait=10 --out=%s %s" % (aria2path, basename, url)
        logging.debug('Aria2 command line: %s' % (s))
        os.system(s)


def yd_get_full(url, output, filename, metadata):
    if output:
        output = output.replace("\"","-")
        os.makedirs(output, exist_ok=True)
    if metadata and output:
        resp = requests.get(YD_API, params={'public_key': url})
        f = open(os.path.join(output, '_metadata.json'), 'w', encoding='utf8')
        f.write(resp.text)
        f.close()
    resp = requests.get(YD_API_DOWNLOAD, params={'public_key': url})
    data = resp.json()
    id = url.rsplit('/', 1)[-1]
    if output is None:
        output = id
    if 'href' in data.keys():
        get_file(data['href'], filepath=output, filename=filename)
    else:
        print('No download url. Probably wrong public url/key?')


BUF_SIZE = 65536

def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(BUF_SIZE), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def sha256(fname):
    hash_sha256 = hashlib.sha256()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(BUF_SIZE), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


def yd_get_and_store_dir(url, path, output, nofiles=False, iterative=False):
    # print(f"requests.get params = {url}, {path}")
    resp = requests.get(YD_API, params={'public_key': url, 'path' : path, 'limit' : 1000})
    arr = [output, ]
    arr.extend(url_to_dir_list(path))
    os.makedirs(os.path.join(*arr), exist_ok=True)
    
    if nofiles: # metadata is written to disk only if --nofiles flag is given
        logging.info('Saving metadata of %s' % (os.path.join(os.path.join(*arr))))
        f = open(os.path.join(os.path.join(*arr), '_metadata.json'), 'w', encoding='utf8')
        f.write(resp.text)
        f.close()
    
    if not iterative:
        return resp.json()
    else:
        data = resp.json()
        if '_embedded' in data.keys():
            for row in data['_embedded']['items']:
                if 'path' in row.keys():
                    if row['type'] == 'dir':
                        arr = [output,]
                        arr.extend(url_to_dir_list(path))
                        row_path = os.path.join(*arr)
                        os.makedirs(row_path, exist_ok=True)
                        if iterative:
                            yd_get_and_store_dir(url, row['path'], output, nofiles, iterative=iterative)
                    elif row['type'] == 'file':
                        if nofiles:
                            continue
                        arr = [output,]
                        arr.extend(url_to_dir_list(row['path']))
                        dir_path = os.path.join(*arr[:-1])
                        file_path = os.path.join(*arr)
                        # print(f"row {row['path']}")
                        # print(f"arr {arr[:-1]}")
                        # print(f"Checking existence of {file_path}")
                        if not os.path.exists(file_path):
                            get_file(row['file'], dir_path, filename=arr[-1], filesize=row['size'])
                            logging.debug('Saved %s' % (row['path']))
                        else:
                            # todo: sha256 of downloaded file
                            # print(f"server size = {row['size']}, md5 = {row['md5']}, sha256 = {row['sha256']}")
                            # print(f"local  size = {os.path.getsize(file_path)}, md5 = {md5(file_path)}, sha256 = {sha256(file_path)}")
                            if os.path.getsize(file_path) != int(row['size']):
                                logging.info(f"File {row['path']} has wrong size, downloading it again..")
                                get_file(row['file'], dir_path, filename=arr[-1], filesize=row['size'])
                            elif sha256(file_path) != row['sha256']:
                                # todo: write all wrong files to some file
                                logging.info(f"File {row['path']} has wrong sha256, downloading it again..")
                                get_file(row['file'], dir_path, filename=arr[-1], filesize=row['size'])
                            else:
                                logging.info('Already stored %s' % (row['path']))

        return

class Project:
    """Disk files extractor. Yandex.Disk only right now"""

    def __init__(self):
        pass

    def configure(self, key, projectdir=None):
        if projectdir is None:
            projectdir = os.getcwd()
        filepath =  os.path.join(projectdir, '.ydiskarc')
        if os.path.exists(filepath):
            f = open(filepath, 'r', encoding='utf8')
            conf = yaml.load(f)
            f.close()
            if 'keys' not in conf.keys():
                conf['keys'] = {}
            conf['keys']['yandex_oauth'] = key
        else:
            conf = {'keys' : {'yandex_oauth' : key}}
        f = open(filepath, 'w', encoding='utf8')
        yaml.safe_dump(conf, f)
        f.close()
        print('Configuration saved at %s' % (filepath))


    def __store(self, url, metapath, nofiles=False):
        # path = "" # always download all the storage
        split_url = url.split("/d/", 1)
        path = "/" + unquote("/".join(split_url[-1].split("/")[1:])) # download only specified path if url contains such path
        if not metapath: # output
            metapath = split_url[-1].split("/")[0]
            url = split_url[0] + "/d/" + metapath # root url
            metapath = metapath.replace("\"","-")
        else:
            uid = split_url[-1].split("/")[0]
            url = split_url[0] + "/d/" + uid
            pass
        logging.info(f"Saving url = {url}  path = {path}  output_path = {metapath}")
        os.makedirs(metapath, exist_ok=True)
        yd_get_and_store_dir(url, path, metapath, nofiles=nofiles, iterative=True)

    def sync(self, url, output, nofiles=False):
        self.__store(url, output, nofiles)
        pass

    def full(self, url, output, filename, metadata):
        yd_get_full(url, output, filename, metadata)
        pass

