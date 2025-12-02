ydiskarc: a command-line tool to backup public resources from Yandex.disk (disk.yandex.ru / yadi.sk) filestorage service
########################################################################################################################

ydiskarc - программа, чтоб скачивать публичные раздачи с яндекс диска. Ибо родной клиент яндекс диска - чудовище. Да и оригинальная версия настоящего клиента https://github.com/ruarxive/ydiskarc не блещет продуманностью и удобством использования.


.. contents::

.. section-numbering::



Main features
=============

* Metadata extraction
* Download any public resource file or directory

Отличия от оригинальной версии
=============

Исправления
-----------

* Оригинальная версия не качает вообще никаких файлов, если задать ключ --update. А если его не задавать, то, напротив, качает все файлы, в т. ч. уже скачанные.
* Кроме того, короткая версия этого ключа -u совпадала с таковой для главного ключа --url.
* Теперь она качает файлы с кавычками в именах. Да, в яндексе попадаются и такие.
* Теперь закачиваемые файлы имеют временное расширение, а затем переименовываются.

Дополнения
----------

* Теперь можно закачивать не всю раздачу, а только одну папку, предоставляя url оной папки из браузера как параметр.

В планах
--------

* Выкинуть флаг --update, ибо я не знаю, кто будет в здравом уме качать без него.
* Проверять md5 и размер файлов (до и после закачки, ибо сейчас она пишет ошибки скачивания прямо вместо файла).
* Проставлять оригинальную дату у файлов.
* Возможность не заводить полный путь на диске. Ибо в раздачах порою встречаются аршинные пути, файлы по которым невозможно сохранить на диск (по крайней мере в винде).
* Проверить возможность скачивания по красивому url, а не только по закодированному процентами. А также url с иероглифами и прочими тайными знаками (и таки да, в той единственной раздаче, которую мне надо было скачать, они тоже встречаются!).
* Возможность отключать сохранение _metadata.json.
* Многопоточная закачка?
* Чтобы не вылетала при одной неудачной закачке, а записывала её имя в лог.
* Чтобы продолжала свою работу после спящего режима.

Installation
============


Any OS
-------------

Проверено в windows 10 и ubuntu 22.04:

.. code-block:: bash
    
    $ git clone https://github.com/dining-philosopher/ydiskarc.git
    $ cd ydiskarc
    $ python3 setup.py build install

ну или

.. code-block:: bash

    $ python3 setup.py build && sudo python3 setup.py install



Python version
--------------

Python version 3.6 or greater is required.

Usage
=====


Synopsis:

.. code-block:: bash

    $ ydiskarc [command] [flags]


See also ``python -m ydiskarc`` and ``ydiskarc [command] --help`` for help for each command.

Commands
========

Sync command
----------------
Synchronizes files and metadata from public resource of directory type to the local directory.


Extracts all files and metadata from "https://disk.yandex.ru/d/VVNMYpZtWtST9Q" resource to the dir "mos9maystyle"

.. code-block:: bash

    $ ydiskarc sync --url https://disk.yandex.ru/d/VVNMYpZtWtST9Q -d -o mos9maystyle

Скачать всю раздачу:

.. code-block:: bash

    ydiskarc sync --url https://disk.yandex.ru/d/ид_раздачи -d

Скачать одну папку:

.. code-block:: bash

    ydiskarc sync --url "https://disk.yandex.ru/d/ид_раздачи/путь/ещё/путь" -d

(копируем url из браузера)

Full command
----------------
Downloads single file or directory. Single file downloaded with original file format. Directory downloaded as ZIP file
with all files inside.

Downloads file from url "https://disk.yandex.ru/i/t_pNaarK8UJ-bQ" and saves it into folder "files" with metadata saved as "_metadata.json"

.. code-block:: bash

    $ ydiskarc full --url https://disk.yandex.ru/i/t_pNaarK8UJ-bQ -o files -v -m

Команда ``ydiskarc full`` не проверялась.


