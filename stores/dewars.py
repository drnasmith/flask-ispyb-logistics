import time

from flask import Blueprint
from flask import render_template
from flask import jsonify
from flask import request

import logs
from ispyb_api import controller

api = Blueprint('stores', __name__, url_prefix='/stores')

jsonfilename = 'logs/stores.json'


"""
Route for vue.js version
"""
@api.route("/vstores")
def vstores():
    return render_template('vue-stores.html', api_prefix="stores")

@api.route('/')
def index():
    """
    Main page for dewar management
    """
    return render_template('stores.html',
                           title="Stores Dewar Management",
                           api_prefix="stores",
                           max_dewar_history=logs.max_stores_dewars
                           )


@api.route('/dewars', methods=["GET", "POST"])
def location():
    result = {}
    status_code = 200

    if request.method == "GET":
        deque_data = logs.readStoresFile(jsonfilename)

        # Marshall the data into a serializable json array with 
        # indexes {1, {}, 2, {}} etc. to match the front end
        for index, item in enumerate(deque_data, 1):
            result[str(index)] = item

    elif request.method == "POST":
        location = request.form['location']
        barcode = request.form['barcode']
        awb = request.form['awb']

        if location and barcode:
            result, status_code = updateDewarLocation(barcode, location, awb)
        else:
            print("Warning barcode and/or location not set, ignoring request.")

            result = {'location': location,
                      'barcode': barcode,
                      'awb': awb,
                      'status': 'fail - location and/or barcode not set',
                      }
            status_code = 400

    return jsonify(result), status_code


def updateDewarLocation(barcode, location, awb=None):
    """
    Update the records for this dewar

    If it gets here we have already tested that the barcode and location are ok.
    """
    # if remote_ip not in allowed_ips:
    #     print json.dumps({'location':location,'barcode':barcode,'awb':awb,'status':'fail','your_ip':remote_ip})
    status_code = 200

    if awb:
        awb = awb.replace('+', '_')

    destination = ''

    barcode_prefix = barcode.upper()[0:2]

    if location.upper() == 'STORES-IN':
        if barcode_prefix == 'SP' or 'I14' in barcode.upper():
            destination = 'I14'
        elif barcode_prefix == 'EM' or any(b in barcode.upper() for b in ['M01', 'M02', 'M03', 'M04', 'M05', 'M06', 'M07']):
            destination = 'eBIC'
        elif barcode_prefix == 'MX' or any(b in barcode.upper() for b in ['I03', 'I04', 'I23', 'I24']):
            destination = 'Zone 6 store'
        else:
            destination = 'Unknown'

    # Next part is new and uses a deque to ensure last 10 dewars are processed
    data = logs.readStoresFile(jsonfilename)

    data.appendleft({'barcode': barcode,
                     'inout': location,
                     'date': time.strftime('%a %d %b, %H:%M:%S'),
                     'destination': destination,
                     'awb': awb})

    result = controller.set_location(barcode, location, awb)

    if result is not None:
        result = {'location': location, 'barcode': barcode, 'awb': awb, 'status': 'ok'}

        # Now we can update the stores logs if no error!
        logs.writeStoresFile(jsonfilename, data)
    else:
        result = {'location': location,
                  'barcode': barcode,
                  'awb': awb,
                  'status': 'fail - controller did not set location',
                  }
        status_code = 400

    return result, status_code
