import logging
import tempfile

from models.base import BaseModel
from sybil import Serie, Sybil
from sybil import __version__ as sybil_version

logger = logging.getLogger('ark')


class Args(object):
    def __init__(self, config_dict):
        self.__dict__.update(config_dict)


class SybilModel(BaseModel):
    def __init__(self, args):
        super().__init__()
        self.__version__ = sybil_version
        self.model = Sybil(name_or_path='test')

    def run_model(self, dicom_files, payload=None):
        dicom_paths = []

        for dicom in dicom_files:
            try:
                dicom_path = tempfile.NamedTemporaryFile(suffix='.dcm').name
                dicom.save(dicom_path)
                dicom_paths.append(dicom_path)
            except Exception as e:
                logger.warning("{}: {}".format(type(e).__name__, e))

        serie = Serie(dicom_paths)
        scores = self.model.predict([serie])

        report = {'predictions': scores}

        return report
