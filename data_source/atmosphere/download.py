from core.scheduler import Scheduler
from ftplib import FTP
import logging as log
import os

class Downloader(Scheduler):
    def __init__(self, path, filename):
        super().__init__(ttl=0)
        self.filename = filename
        self.path = path

    def _download_noaa(self, progress, year):
        fname = self.filename(year)
        ftp = FTP('ftp2.psl.noaa.gov')
        log.debug('FTP login: '+ftp.login())
        log.info(f'Downloading file: {fname}')
        ftp.cwd(f'Datasets/ncep.reanalysis/{self.path}')
        progress[1] += ftp.size(fname)
        with open(os.path.join('tmp/ncep', fname), 'wb') as file:
            def write(data):
               file.write(data)
               progress[0] += len(data)
            ftp.retrbinary(f'RETR {fname}', write)
        log.info(f'Downloaded file: {fname}')

    def download(self, year):
        if eq := self.get(year):
            return eq
        return self.query_tasks(year, [(self._download_noaa, (year,), f'downloading {year}.nc', True)])
