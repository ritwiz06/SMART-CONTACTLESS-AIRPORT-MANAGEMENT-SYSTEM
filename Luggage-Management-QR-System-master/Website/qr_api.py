import qrcode
import mongo_api
import io
import base64

def save_qr_to_mongo(luggage_id, flight_id):
    img = qrcode.make(luggage_id)
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    print(type(img))
    print(img_bytes)

    encoded_img_data = base64.b64encode(img_bytes.getvalue())

    image = {
        'qr_id': luggage_id,
        'flight_id': flight_id,
        'data': encoded_img_data
    }

    print(image)

    image_id = mongo_api.qr_images.insert_one(image).inserted_id