from flask import Flask, request, render_template, send_file, redirect, url_for, flash
import mongo_api
import qr_api
import helpdesk_api
import knapsack
import io
import qrcode
from PIL import Image
import base64

generator = True

app = Flask(__name__, static_url_path='/static')
app.config['PROPAGATE_EXCEPTIONS'] = True

#####################################################
#                 WEBSITE API                       #
#####################################################

@app.route('/luggage_of_<fname>', methods = ['GET'])
def luggage_page(fname):
    luggage_data = list(mongo_api.Luggage.find({'flight_id': mongo_api.get_obj_id(fname)}))
    qr_images = list(mongo_api.qr_images.find({'flight_id': fname}))

    for bag in luggage_data:
        for qr in qr_images:
            if str(bag['_id'])==str(qr['qr_id']):
                bag['qr_data'] = qr['data'].decode('utf-8')

    #print(luggage_data)
    #print(qr_images)

    return render_template('luggage_page.html', luggage = luggage_data, fname = fname, qr_images=qr_images)

@app.route('/add_luggage_<fname>', methods = ['GET', 'POST'])
def add_luggage(fname):
    if request.method == 'GET':
        return render_template('add_luggage.html', fname = fname)
    else:
        _flight_id = mongo_api.get_obj_id(request.form['flight_id'])
        _owner = request.form['owner']
        _weight = request.form['weight']
        _height = request.form['height']
        _width = request.form['width']
        _breadth = request.form['breadth']
        luggage =  {
            'flight_id': _flight_id,
            'owner': _owner,
            'weight': _weight,
            'dimension': {
                'height': _height,
                'width': _width,
                'breadth': _breadth
            },
            'container_no': 0,
            'scans': {
                'scan1': {
                    'is_scanned': False,
                },
                'scan2': {
                    'is_scanned': False,
                },
                'scan3': {
                    'is_scanned': False,
                },
                'scan4': {
                    'is_scanned': False,
                }
            },
            'total_scans': 0
        }
        mongo_api.Luggage.insert_one(luggage)
        luggage_id = str(mongo_api.Luggage.find_one(luggage)['_id'])
        qr_api.save_qr_to_mongo(luggage_id, fname)
        
        # id = mongo_api.grid_fs.put()
        # metadata = {
        #     'id':id,
        #     'name': _name,
        # }
        # status = mongo_api.qr_db.insert_one(metadata)
        # if status:
        #     print('Image uploaded successfully')
        # print('Image not uploaded successfully')

    return redirect(url_for('luggage_page', fname = fname))
    
@app.route('/delete_bag_<id>_<fname>', methods =['GET', 'POST'])
def delete_bad(id, fname):
    _id = mongo_api.get_obj_id(id)
    mongo_api.Luggage.delete_one({'_id': _id})
    return redirect(url_for('luggage_page', fname = fname))

@app.route('/flights', methods = ['GET'])
def flights_page():
    return render_template('flights_page.html', flights = get_flights())

@app.route('/add_flight', methods = ['GET', 'POST'])
def add_flights():
    if request.method == 'GET':
        return render_template('add_flight.html')
    else:
        _name = request.form['name']
        _from = request.form['from']
        _to = request.form['to']
        _date = request.form['date']
        _time = request.form['time']
        flight = {
            'name': _name,
            'to': _to,
            'from': _from,
            'date': str(_date),
            'time': str(_time)
        }
        mongo_api.Flights.insert_one(flight)
    return redirect(url_for('flights_page'))        

@app.route('/delete_flight_<id>', methods = ['GET', 'POST'])
def delete_flight(id):
    _id = mongo_api.get_obj_id(id)
    mongo_api.Flights.delete_one({'_id': _id})
    return redirect(url_for('flights_page'))

@app.route('/login', methods = ['GET'])
def login_page():
    return render_template("login.html")


@app.route('/sign_up', methods= ['GET'])
def signup_page():
    return render_template("sign_up.html")
    
@app.route('/signup_form', methods=['GET','POST'])
def signup():
    if(request.method=='POST'):
        username = request.form['username']
        password = request.form['password']
        newuser = {
            'username': username,
            'password': password,
            'generator':False
        }
        mongo_api.user_db.insert_one(newuser)
        print("inserted new user")
        return redirect(url_for('login_page'))

@app.route('/login_form', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_check = get_password_generator(username)
        if password == password_check:
            return redirect(url_for('flights_page'))
        else:
            return redirect(url_for('login_page'))
    else:
        return redirect(url_for('login_page'))

@app.route('/helpdesk', methods = ['GET', 'POST'])
def helpdesk_page():
    if request.method == 'POST':
        _email = str(request.form['email'])
        _full_name = str(request.form['full_name'])
        _flight = str(request.form['flight'])
        _seat  = str(request.form['seat'])
        _message = str(request.form['message'])
        helpdesk_api.insert_msg(_email, _flight,  _message)
    return render_template('helpdesk_page.html')

@app.route('/')
def landing_page():
    return redirect(url_for('login'))

#####################################################
#                     FTP API                       #
#####################################################

@app.route('/luggage_icon.png', methods = ['GET'])
def get_luggage_icon():
    return send_file('.\\templates\\luggage_icon.png')

@app.route('/favicon.ico', methods = ['GET'])
def get_favicon():
    return send_file('.\\templates\\luggage_icon.ico')

@app.route('/qr_img_<id>.png', methods = ['GET'])
def get_qr_image(id):
    print('/static/qr/qr_img_' + str(id) + '.png')
    return send_file('static/qr/qr_img_' + str(id) + '.png')

#####################################################
#                   MONGO API                       #
#####################################################

def get_flights():
    return list(mongo_api.Flights.find({}))
    
def get_password_generator(username):
    generator = bool(mongo_api.user_db.find_one({'username': username})['generator'])
    print("role is: ", generator)
    return mongo_api.user_db.find_one({'username': username})['password']

#####################################################
#                   SCANNER API                     #
#####################################################

@app.route('/api', methods = ['GET'])
def flutter_api():
    id = str(request.args['data'])
    print(id)
    bag = mongo_api.Luggage.find_one({'_id': mongo_api.get_obj_id(id)})
    flight_name = str(mongo_api.Flights.find_one({'_id': bag['flight_id']})['name'])
    result = str(bag['owner']) + ',' + str(bag['weight']) + ',' + str(bag['dimension']['width']) + ',' + str(bag['dimension']['height']) + ',' + str(bag['dimension']['breadth']) + ',' + str(bag['container_no']) + ',' + flight_name
    return result
    
#####################################################
#                  KNAPSACK API                     #
#####################################################

@app.route('/knapsack_<id>')
def call_knapsack(id):
    luggage = list(mongo_api.Luggage.find({'flight_id': mongo_api.get_obj_id(id)}))
    result = knapsack.knapsack(luggage)
    for bag in result:
        mongo_api.Luggage.update(
            {'_id': bag['_id']},
            {
                '$set': {
                    'container_no': bag['container_no']
                }
            },upsert=True
        )
    return redirect(url_for('luggage_page', fname = id))

@app.route('/test_qr')
def save_qr():
    img = qrcode.make('test text')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    print(type(img))
    print(img_bytes)

    encoded_img_data = base64.b64encode(img_bytes.getvalue())

    image = {
        'data': encoded_img_data
    }

    print(image)

    image_id = mongo_api.qr_images.insert_one(image).inserted_id
    return "<h1> Qr saved !</h1>"

@app.route('/read_qr')
def read_qr():
    img = mongo_api.qr_images.find_one()
    pil_img = img['data']#.decode('utf-8')

    print(pil_img)

    return f'<h1> QR: </h1><img src="data:image/png;base64,{ pil_img }" alt="error">  </img>'


mode="production"

if __name__ == '__main__':
    mongo_api.main()
    if mode=="dev":
        app.run()
    else:
        app.run()
