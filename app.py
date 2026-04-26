
from evaluation import evaluate_report, evaluation_prompt
from flask import Flask, send_from_directory, request, jsonify, Response, stream_with_context, send_file
from flask_cors import CORS
import os, time, json, re
from interview_simulator import stream_interview
from cache import create_cache_zip
from medgemma import medgemma_get_text_response

app = Flask(__name__, static_folder=os.environ.get("FRONTEND_BUILD", "frontend/build"), static_url_path="/")
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})

@app.route("/")
def serve():
    """Serves the main index.html file."""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/stream_conversation", methods=["GET"])
def stream_conversation():
    """Streams the conversation with the interview simulator."""
    patient = request.args.get("patient", "Patient")
    condition = request.args.get("condition", "unknown condition")
    
    def generate():
        try:
            for message in  stream_interview(patient, condition):
                yield f"data: {message}\n\n"
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"
            raise e
            
    return Response(stream_with_context(generate()), mimetype="text/event-stream")

@app.route("/api/evaluate_report", methods=["POST"])
def evaluate_report_call():
    """Evaluates the provided medical report."""
    data = request.get_json()
    report = data.get("report", "")
    if not report:
        return jsonify({"error": "Report is required"}), 400
    condition = data.get("condition", "")
    if not condition:
        return jsonify({"error": "Condition is required"}), 400    
    
    evaluation_text = evaluate_report(report, condition)
    
    return jsonify({"evaluation": evaluation_text})


@app.route("/api/download_cache")
def download_cache_zip():
    """Creates a zip file of the cache and returns it for download."""
    zip_filepath, error = create_cache_zip()
    if error:
        return jsonify({"error": error}), 500
    if not os.path.isfile(zip_filepath):
        return jsonify({"error": f"File not found: {zip_filepath}"}), 404
    return send_file(zip_filepath, as_attachment=True)


@app.route("/<path:path>")
def static_proxy(path):
    """Serves static files and defaults to index.html for unknown paths."""
    file_path = os.path.join(app.static_folder, path)
    if os.path.isfile(file_path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, "index.html")
        
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860, threaded=True)
