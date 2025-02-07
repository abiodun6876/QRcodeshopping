from flask import Flask, render_template, request, jsonify, send_file
import cv2
import numpy as np
import pandas as pd
import qrcode
from io import BytesIO
from pyzbar.pyzbar import decode
from reportlab.pdfgen import canvas

app = Flask(__name__)

# CSV file as Database
CSV_FILE = "products.csv"
scanned_items = []  # List to store scanned products

# Load product database from CSV
def load_products():
    return pd.read_csv(CSV_FILE, dtype=str)

# Generate QR Code for a product
@app.route("/generate_qr/<product_id>")
def generate_qr(product_id):
    df = load_products()
    product = df[df["id"] == product_id]
    
    if product.empty:
        return "Product not found", 404
    
    qr_url = f"https://q-rcodeshopping.vercel.app/scan_product/{product_id}"
    qr = qrcode.make(qr_url)

    img_io = BytesIO()
    qr.save(img_io, 'PNG')
    img_io.seek(0)

    return send_file(img_io, mimetype='image/png')

# Scan Barcode/QR Code
@app.route("/scan", methods=["POST"])
def scan_barcode():
    global scanned_items
    file = request.files["file"]
    
    image = cv2.imdecode(np.frombuffer(file.read(), np.uint8), cv2.IMREAD_COLOR)
    barcodes = decode(image)

    df = load_products()
    for barcode in barcodes:
        barcode_data = barcode.data.decode("utf-8")
        product = df[df["id"] == barcode_data]

        if not product.empty:
            scanned_items.append({"id": barcode_data, "name": product.iloc[0]["name"], "price": float(product.iloc[0]["price"])})

    total_price = sum(item["price"] for item in scanned_items)
    return jsonify({"items": scanned_items, "total": total_price})

# Print Receipt (HTML)
@app.route("/receipt")
def print_receipt():
    total_price = sum(item["price"] for item in scanned_items)
    return render_template("receipt.html", items=scanned_items, total=total_price)

# Generate PDF Receipt
@app.route("/receipt/pdf")
def generate_pdf():
    pdf_io = BytesIO()
    c = canvas.Canvas(pdf_io)
    c.drawString(100, 750, "Shopping Receipt")
    y = 730
    for item in scanned_items:
        c.drawString(100, y, f"{item['name']} - ${item['price']}")
        y -= 20
    c.drawString(100, y - 20, f"Total: ${sum(item['price'] for item in scanned_items)}")
    c.showPage()
    c.save()

    pdf_io.seek(0)
    return send_file(pdf_io, mimetype="application/pdf", as_attachment=True, download_name="receipt.pdf")

# Clear Cart
@app.route("/clear", methods=["POST"])
def clear_cart():
    global scanned_items
    scanned_items = []
    return jsonify({"message": "Cart cleared"})

if __name__ == "__main__":
    app.run(debug=True)
