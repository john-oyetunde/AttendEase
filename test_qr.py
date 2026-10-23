import qrcode

message = "AttendEase QR code is working!"

qr = qrcode.make(message)

qr.save("qrcodes/test_qr.png")

print("Success! Your first QR code has been created.")