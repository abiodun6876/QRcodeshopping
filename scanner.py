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
    app.logger.info("Loading products from CSV file.")
    return pd.read_csv(CSV_FILE, dtype=str)

# Generate QR Code for a product
@app.route("/generate_qr/<product_id>")
def generate_qr(product_id):
    app.logger.info(f"Generating QR code for product ID: {product_id}")
    df = load_products()
    product = df[df["id"] == product_id]
    
    if product.empty:
        app.logger.error(f"Product with ID {product_id} not found.")
        return "Product not found", 404
    
    qr_url = f"https://q-rcodeshopping.vercel.app/scan_product/{product_id}"
    qr = qrcode.make(qr_url)

    img_io = BytesIO()
    qr.save(img_io, 'PNG')
    img_io.seek(0)

    app.logger.info(f"QR code generated for product ID: {product_id}")
    return send_file(img_io, mimetype='image/png')

# Scan Barcode/QR Code
@app.route("/scan", methods=["POST"])
def scan_barcode():
    global scanned_items
    app.logger.info("Starting barcode scan.")
    file = request.files["file"]
    
    image = cv2.imdecode(np.frombuffer(file.read(), np.uint8), cv2.IMREAD_COLOR)
    barcodes = decode(image)

    df = load_products()
    for barcode in barcodes:
        barcode_data = barcode.data.decode("utf-8")
        product = df[df["id"] == barcode_data]

        if not product.empty:
            scanned_items.append({"id": barcode_data, "name": product.iloc[0]["name"], "price": float(product.iloc[0]["price"])})
            app.logger.info(f"Scanned product: {product.iloc[0]['name']}")

    total_price = sum(item["price"] for item in scanned_items)
    app.logger.info(f"Total price of scanned items: {total_price}")
    return jsonify({"items": scanned_items, "total": total_price})

# Print Receipt (HTML)
@app.route("/receipt")
def print_receipt():
    total_price = sum(item["price"] for item in scanned_items)
    app.logger.info(f"Generating receipt with total price: {total_price}")
    return render_template("receipt.html", items=scanned_items, total=total_price)

# Generate PDF Receipt
@app.route("/receipt/pdf")
def generate_pdf():
    app.logger.info("Generating PDF receipt.")
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
    app.logger.info("PDF receipt generated successfully.")
    return send_file(pdf_io, mimetype="application/pdf", as_attachment=True, download_name="receipt.pdf")

# Clear Cart
@app.route("/clear", methods=["POST"])
def clear_cart():
    global scanned_items
    scanned_items = []
    app.logger.info("Cart cleared.")
    return jsonify({"message": "Cart cleared"})

# Starting Flask application
app.logger.info("Flask app starting.")
