from flask_cors import CORS

cors = CORS(resources={r"/*": {"origins": "*"}})

# CORS(
#     app,
#     resources={r"/*": {"origins": ["http://localhost:3000"]}},
#     supports_credentials=True,
#     allow_headers=["Content-Type", "Authorization"],
#     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
# )