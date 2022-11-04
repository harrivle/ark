import json
import logging
import time
import tracemalloc

from flask import Flask
from flask import request

from api import __version__ as api_version
from api.utils import dicom_dir_walk, download_zip, validate_post_request
from models import model_dict


def set_model(app):
    model_name = app.config['MODEL_NAME']
    model_args = app.config['MODEL_ARGS']

    if model_name in model_dict:
        app.config['MODEL'] = model_dict[model_name](model_args)
    else:
        raise KeyError("Model '{}' not found in model dictionary".format(model_name))


def set_routes(app):
    @app.route('/serve', methods=['POST'])  # TODO: Legacy endpoint, remove on 1.0
    @app.route('/dicom/files', methods=['POST'])
    def dicom():
        """Endpoint to upload physical files
        """
        start = time.time()

        app.logger.info("Request received at /dicom/files")
        response = {'data': None, 'message': None, 'statusCode': 200}
        model = app.config['MODEL']

        try:
            snapshot1 = tracemalloc.take_snapshot()
            print('form: ', request.form.to_dict())
            print('files: ', request.files)
            validate_post_request(request, required=model.required_data)

            app.logger.debug("Received JSON payload: {}".format(request.form.to_dict()))
            payload = json.loads(request.form['data'])

            dicom_files = request.files.getlist("dicom")
            # TODO: Must receive four files
            app.logger.debug("Received {} files".format(len(dicom_files)))

            response["data"] = model.run_model(dicom_files, payload=payload)

            snapshot2 = tracemalloc.take_snapshot()

            top_stats = snapshot2.compare_to(snapshot1, 'lineno')

            for stat in top_stats[:5]:
                app.logger.debug(stat)

            curr, peak = tracemalloc.get_traced_memory()
            if 'CURR' not in app.config:
                app.config['CURR'] = curr/(1024*1024)
                app.config['PEAK'] = peak/(1024*1024)

            app.logger.debug("Current Mem: {}, Peak Mem: {}".format(curr/(1024*1024), peak/(1024*1024)))
            app.logger.debug("Current Mem Diff: {}, Peak Mem Diff: {}".format((curr-app.config['CURR'])/(1024*1024), (peak-app.config['PEAK'])/(1024*1024)))
        except Exception as e:
            msg = "{}: {}".format(type(e).__name__, e)
            app.logger.error(msg)
            response['message'] = msg
            response['statusCode'] = 400

        response['runtime'] = "{:.2f}s".format(time.time() - start)

        return response, response['statusCode']

    @app.route('/dicom/uri', methods=['POST'])
    def dicom_uri():
        """Endpoint to send a link to an archive file containing DICOM files
        """
        start = time.time()

        app.logger.info("Request received at /dicom/uri")
        response = {'data': None, 'message': None, 'statusCode': 200}
        model = app.config['MODEL']

        try:
            payload = request.get_json()
            app.logger.debug("Received JSON payload: {}".format(payload))

            download_zip(payload['uri'])
            dicom_files = dicom_dir_walk()

            response["data"] = model.run_model(dicom_files, payload=payload)
        except Exception as e:
            msg = "{}: {}".format(type(e).__name__, e)
            app.logger.error(msg)
            response['message'] = msg
            response['statusCode'] = 400

        response['runtime'] = "{:.2f}s".format(time.time() - start)

        return response, response['statusCode']

    @app.route('/info', methods=['GET'])
    def info():
        """Endpoint to return general info of the API
        """
        app.logger.info("Request received at /info")
        response = {'data': None, 'message': None, 'statusCode': 200}

        try:
            info_dict = {
                'apiVersion': app.config['API_VERSION'],
                'modelName': app.config['MODEL_NAME'],
                'modelVersion': app.config['MODEL'].__version__,
            }

            response['data'] = info_dict
        except Exception as e:
            msg = "{}: {}".format(type(e).__name__, e)
            app.logger.error(msg)
            response['message'] = msg
            response['statusCode'] = 400

        return response['statusCode']


def build_app(config):
    app = Flask('ark')
    app.config.from_mapping(config)
    logging.getLogger('ark').setLevel(logging.DEBUG)

    app.config['API_VERSION'] = api_version
    set_model(app)
    set_routes(app)

    return app
