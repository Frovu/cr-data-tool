from core.scheduler import Scheduler
from ftplib import FTP
import logging as log
import os

class Downloader(Scheduler):
    def __init__(self, ttl=0):
        super().__init__(ttl=ttl)

    def download(self, year):
        if eq := self.get(year):
            return eq
        return self.query_tasks(year, [(_download_model, (year,), f'downloading {year}.nc', True)])

def filename(year):
    return f'air.{year}.nc'

def _download_model(progress, year):
    fname = filename(year)
    ftp = FTP('ftp2.psl.noaa.gov')
    log.debug('FTP login: '+ftp.login())
    log.info(f'Downloading file: {fname}')
    ftp.cwd('Datasets/ncep.reanalysis/pressure')
    progress[1] += ftp.size(fname)
    with open(os.path.join('tmp', fname), 'wb') as file:
        def write(data):
           file.write(data)
           progress[0] += len(data)
        ftp.retrbinary(f'RETR {fname}', write)
    log.info(f'Downloaded file: {fname}')
