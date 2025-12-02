import logging

import yaml
import requests
import os.path
import json
import re
from os.path import expanduser
import shutil
from rich.progress import Progress, TextColumn

from urllib.parse import unquote



# TODO: ПРОЕКТ "ПРОИЗВОДСТВЕННАЯ РОССИЯ"
# TODO: size!!!!!1 date? md5 sha256?
# TODO: дату изменения менять на правильную?
# TODO: многопоточность и шоп целиком завершалось по первому требованию! и шоп не висло после сна!
# TODO: шоп не вываливалось целиком ежели не получилось скачать один файл! а записывало это в лог



YD_API = 'https://cloud-api.yandex.net/v1/disk/public/resources'
YD_API_DOWNLOAD = 'https://cloud-api.yandex.net/v1/disk/public/resources/download'

REQUEST_HEADER = {'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Mobile Safari/537.36'}
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
        page = requests.get(url, params, headers=REQUEST_HEADER, stream=True, verify=True)
    else:
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
    if not aria2:
        filename_tmp = filename + ".ydiskarc_download"
        f = open(filename_tmp, 'wb')
        total = 0
        chunk = 0
        for line in page.iter_content(chunk_size=DEFAULT_CHUNK_SIZE):
            chunk += 1
            if line:
                f.write(line)
            total += len(line)
            if filesize is not None:
#               logging.info('File %s to size %d' % (filename, total))               
                progress.update(task1, advance=len(line))
            if chunk % 1000 == 0:
                # logging.info('File %s to size %d' % (filename, total))
                print(".", end = "")
                pass
        f.close()
        os.rename(filename_tmp, filename)
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

def yd_get_and_store_dir(url, path, output, update=True, nofiles=False, iterative=False):
    # print(f"path = {path}")
    # if output:
    #     output = output.replace("\"","-")
    id = url.rsplit('/', 1)[-1] # not needed ?????????????????????
    print(f"requests.get params = {url}, {path}")
    resp = requests.get(YD_API, params={'public_key': url, 'path' : path, 'limit' : 1000})
    arr = [output, ]
    # arr.extend([i.rstrip().replace("\"","-") for i in path.split('/')])
    arr.extend(url_to_dir_list(path))
    os.makedirs(os.path.join(*arr), exist_ok=True)
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
                        # arr.extend([i.rstrip().replace("\"","-") for i in path.split('/')])
                        arr.extend(url_to_dir_list(path))
                        row_path = os.path.join(*arr)
                        os.makedirs(row_path, exist_ok=True)
                        if iterative:
                            yd_get_and_store_dir(url, row['path'], output, update, nofiles, iterative=iterative)
                    elif row['type'] == 'file':
                        if nofiles:
                            continue
                        arr = [output,]
                        # arr.extend([i.rstrip().replace("\"","-") for i in row['path'].split('/')])
                        arr.extend(url_to_dir_list(row['path']))
                        dir_path = os.path.join(*arr[:-1])
                        file_path = os.path.join(*arr)
                        # print(f"row {row['path']}")
                        # print(f"arr {arr[:-1]}")
                        # print(f"Checking existence of {file_path}")
                        if not os.path.exists(file_path) or not update:
                            get_file(row['file'], dir_path, filename=arr[-1], filesize=row['size'])
                            logging.info('Saved %s' % (row['path']))
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


    def __store(self, url, metapath, update=False, nofiles=False):
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
        print(f"__store url = {url}  path = {path}  metapath = {metapath}")
        logging.info('Saving %s' % (url))
        os.makedirs(metapath, exist_ok=True)
        id = url.rsplit('/', 1)[-1] # not needed ?????????????????????
        yd_get_and_store_dir(url, path, metapath, update=update, nofiles=nofiles, iterative=True)

    def sync(self, url, output, update=False, nofiles=False):
        # print(f"update = {update}")
        self.__store(url, output, update, nofiles)
        pass

    def full(self, url, output, filename, metadata):
        yd_get_full(url, output, filename, metadata)
        pass

